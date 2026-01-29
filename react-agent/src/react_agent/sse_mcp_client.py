"""SSE MCP 클라이언트 구현 - 재연결 + 세션 유지"""

import json
import httpx
import asyncio
import logging
from typing import Any, Dict, Optional, Callable
from asyncio import Queue
from datetime import datetime

logger = logging.getLogger(__name__)


class SSEMCPClient:
    """
    SSE 방식 MCP 클라이언트
    
    특징:
    - JSON-RPC 2.0 표준 준수
    - 자동 재연결 (무한 재시도)
    - 세션 영속성 (연결 끊겨도 세션 유지)
    - Ping-Pong keep-alive
    - 백그라운드 작업 관리
    """

    def __init__(
        self,
        base_url: str,
        enterprise_id: Optional[str] = None,
        api_key: Optional[str] = None,
        on_reconnect: Optional[Callable] = None,
        auto_reconnect: bool = True
    ):
        """
        Args:
            base_url: MCP 서버 URL
            enterprise_id: Enterprise ID (SSE 연결에 필요)
            api_key: API 키
            on_reconnect: 재연결 후 호출될 콜백 함수
            auto_reconnect: 자동 재연결 활성화 (기본: True)
        """
        self.base_url = base_url.rstrip("/")
        self.enterprise_id = enterprise_id
        self.api_key = api_key
        self.on_reconnect = on_reconnect
        self.auto_reconnect = auto_reconnect
        
        # 세션 관리
        self.session_id: Optional[str] = None
        self.is_initialized = False
        self.request_id = 0
        
        # SSE 연결 관리
        self.sse_task: Optional[asyncio.Task] = None
        self.sse_client: Optional[httpx.AsyncClient] = None
        self.running = False
        
        # JSON-RPC 요청-응답 매칭
        self.pending_requests: Dict[int, asyncio.Future] = {}
        
        # 재연결 관리 (무한 재시도)
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 60.0  # 최대 60초 대기
        self.base_reconnect_delay = 1.0  # 초기 1초
        self.last_activity = 0.0
        
        # Pong 워커
        self.pong_queue: Queue = Queue()
        self.pong_worker_task: Optional[asyncio.Task] = None
        self.pong_client: Optional[httpx.AsyncClient] = None
        
        # 연결 모니터
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_interval = 30.0  # 30초마다 헬스체크
        self.idle_timeout = 90.0  # 90초 동안 활동 없으면 경고
        
        # 통계
        self.stats = {
            "total_reconnects": 0,
            "pings_received": 0,
            "pongs_sent": 0,
            "pongs_failed": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "last_reconnect_time": None,
            "uptime_start": None
        }

    def _next_id(self) -> int:
        """JSON-RPC 요청 ID 생성"""
        self.request_id += 1
        return self.request_id

    def _get_headers(self) -> Dict[str, str]:
        """HTTP 요청 헤더"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _create_jsonrpc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        JSON-RPC 2.0 표준 요청 생성
        
        Args:
            method: 메서드 이름
            params: 파라미터 (선택)
            request_id: 요청 ID (None이면 notification)
        
        Returns:
            JSON-RPC 2.0 형식의 딕셔너리
        """
        request = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params is not None:
            request["params"] = params
        
        if request_id is not None:
            request["id"] = request_id
        
        return request

    def _create_jsonrpc_response(
        self,
        request_id: int,
        result: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        JSON-RPC 2.0 표준 응답 생성
        
        Args:
            request_id: 요청 ID
            result: 성공 결과
            error: 에러 정보
        
        Returns:
            JSON-RPC 2.0 형식의 응답
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result if result is not None else {}
        
        return response

    async def _pong_worker(self):
        """백그라운드 Pong 전송 워커"""
        logger.info("[Pong Worker] 🏓 시작")
        
        # Pong 전송 전용 HTTP 클라이언트 (재사용)
        self.pong_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=10.0,
                write=10.0,
                pool=5.0
            ),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                keepalive_expiry=30.0
            )
        )

        try:
            while self.running:
                try:
                    # 큐에서 pong 메시지 가져오기
                    pong_message = await asyncio.wait_for(
                        self.pong_queue.get(),
                        timeout=1.0
                    )
                    
                    # Pong 전송 (재시도 포함)
                    await self._send_pong_with_retry(pong_message)
                    self.pong_queue.task_done()
                    
                except asyncio.TimeoutError:
                    continue
                    
                except Exception as e:
                    logger.error(f"[Pong Worker] 오류: {e}", exc_info=True)
                    
        finally:
            if self.pong_client:
                await self.pong_client.aclose()
                self.pong_client = None
            logger.info("[Pong Worker] 🏓 종료")

    async def _send_pong_with_retry(
        self,
        pong_message: Dict[str, Any],
        max_retries: int = 3
    ):
        """
        Pong 전송 (재시도 로직 포함)
        
        Args:
            pong_message: JSON-RPC 2.0 형식의 pong 응답
            max_retries: 최대 재시도 횟수
        """
        if not self.session_id:
            logger.warning("[Pong] 세션 ID 없음 - 전송 불가")
            return

        ping_id = pong_message.get("id")
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/mcp/message?sessionId={self.session_id}"
                
                response = await self.pong_client.post(
                    url,
                    json=pong_message,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    logger.info(f"[Pong] ✅ 전송 성공 (ID={ping_id})")
                    self.stats["pongs_sent"] += 1
                    return
                else:
                    logger.warning(
                        f"[Pong] ❌ 전송 실패 (ID={ping_id}): "
                        f"status={response.status_code}"
                    )
                    
                    # 4xx 에러는 재시도 불필요
                    if 400 <= response.status_code < 500:
                        self.stats["pongs_failed"] += 1
                        return

            except httpx.TimeoutException as e:
                logger.warning(
                    f"[Pong] 타임아웃 (시도 {attempt + 1}/{max_retries}): {e}"
                )
                
            except Exception as e:
                logger.error(
                    f"[Pong] 오류 (시도 {attempt + 1}/{max_retries}): {e}"
                )
            
            # 재시도 전 대기 (지수 백오프)
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                await asyncio.sleep(wait_time)
        
        # 최종 실패
        logger.error(f"[Pong] 💥 전송 최종 실패 (ID={ping_id})")
        self.stats["pongs_failed"] += 1

    async def _read_sse_with_timeout(self, response, idle_timeout: float = 90.0):
        """
        SSE 스트림 읽기 (idle 타임아웃 적용)
        
        Args:
            response: httpx response 스트림
            idle_timeout: 최대 idle 시간 (초)
            
        Yields:
            SSE 스트림의 각 라인
            
        Raises:
            asyncio.TimeoutError: idle 타임아웃 발생
        """
        line_iterator = response.aiter_lines()

        while True:
            try:
                line = await asyncio.wait_for(
                    line_iterator.__anext__(),
                    timeout=idle_timeout
                )
                yield line
            except StopAsyncIteration:
                logger.info("[SSE] 스트림 정상 종료")
                break
            except asyncio.TimeoutError:
                logger.warning(
                    f"[SSE] ⚠️  Idle 타임아웃 ({idle_timeout}초 동안 데이터 없음)"
                )
                raise

    async def _sse_listener(self):
        """
        SSE 스트림 리스너 (자동 재연결)
        
        연결이 끊기면 자동으로 재연결을 시도합니다.
        세션 ID가 있으면 기존 세션을 재사용하고,
        없으면 새로운 세션을 생성합니다.
        """
        logger.info("[SSE Listener] 시작")

        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }

        while self.running:
            try:
                # SSE 클라이언트 생성
                self.sse_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=10.0,
                        read=None,  # SSE는 무제한
                        write=10.0,
                        pool=5.0
                    ),
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        keepalive_expiry=30.0
                    )
                )

                # 재연결 정보 로깅
                if self.reconnect_attempts > 0:
                    logger.info(
                        f"[SSE Listener] 재연결 시도 #{self.reconnect_attempts}"
                    )
                else:
                    logger.info("[SSE Listener] 초기 연결 시도")

                # SSE 연결
                sse_url = f"{self.base_url}/mcp/sse"
                params = {}

                if self.enterprise_id:
                    params['enterpriseId'] = self.enterprise_id
                    logger.info(f"[SSE] Enterprise ID: {self.enterprise_id}")

                async with self.sse_client.stream(
                    "GET",
                    sse_url,
                    params=params,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        logger.error(
                            f"❌ MCP SSE 연결 실패: {response.status_code}"
                        )
                        raise Exception(f"SSE connection failed: {response.status_code}")

                    logger.info("✅ MCP 연결 성공")
                    
                    # 재연결 성공 시 카운터 리셋
                    if self.reconnect_attempts > 0:
                        self.stats["total_reconnects"] += 1
                        self.stats["last_reconnect_time"] = datetime.now()
                        logger.info(
                            f"[SSE Listener] 재연결 완료 "
                            f"(총 {self.stats['total_reconnects']}번 재연결)"
                        )
                    
                    self.reconnect_attempts = 0

                    # 활동 시간 초기화
                    try:
                        self.last_activity = asyncio.get_running_loop().time()
                    except RuntimeError:
                        import time
                        self.last_activity = time.time()

                    current_event = None

                    # SSE 메시지 처리
                    async for line in self._read_sse_with_timeout(
                        response,
                        idle_timeout=self.idle_timeout
                    ):
                        if not self.running:
                            return

                        # 활동 시간 업데이트
                        try:
                            self.last_activity = asyncio.get_running_loop().time()
                        except RuntimeError:
                            import time
                            self.last_activity = time.time()

                        line = line.strip()
                        if not line:
                            continue

                        # SSE event 필드
                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                            continue

                        # SSE data 필드
                        if line.startswith("data:"):
                            data_str = line[5:].strip()

                            # endpoint 이벤트: 세션 ID 추출
                            if current_event == "endpoint":
                                if "sessionId=" in data_str:
                                    old_session = self.session_id
                                    self.session_id = data_str.split("sessionId=")[1].split("&")[0]

                                    if old_session and old_session != self.session_id:
                                        logger.warning(
                                            f"⚠️ MCP 세션 변경: {old_session[:8]}... → {self.session_id[:8]}..."
                                        )

                                        # 🔥 세션이 변경되었으므로 이전 세션의 pong 큐 비우기
                                        if not self.pong_queue.empty():
                                            old_pongs = self.pong_queue.qsize()
                                            logger.warning(
                                                f"[SSE] 세션 변경으로 {old_pongs}개 pong 메시지 폐기"
                                            )
                                            while not self.pong_queue.empty():
                                                try:
                                                    self.pong_queue.get_nowait()
                                                    self.pong_queue.task_done()
                                                except asyncio.QueueEmpty:
                                                    break

                                        # 🔥 Pending requests도 취소 (이전 세션의 요청들)
                                        if self.pending_requests:
                                            logger.warning(
                                                f"[SSE] 세션 변경으로 {len(self.pending_requests)}개 요청 취소"
                                            )
                                            for req_id, future in list(self.pending_requests.items()):
                                                if not future.done():
                                                    future.set_exception(
                                                        Exception("Session changed - request cancelled")
                                                    )
                                            self.pending_requests.clear()
                                else:
                                    logger.warning(f"⚠️ MCP endpoint에 sessionId 없음")
                                continue

                            # message 이벤트: JSON-RPC 메시지 처리
                            if current_event == "message":
                                try:
                                    msg = json.loads(data_str)
                                    
                                    # JSON-RPC 2.0 검증
                                    if msg.get("jsonrpc") != "2.0":
                                        logger.warning(
                                            f"[SSE] 잘못된 JSON-RPC 버전: "
                                            f"{msg.get('jsonrpc')}"
                                        )
                                        continue
                                    
                                    self.stats["messages_received"] += 1
                                    
                                    # Ping 메시지 처리
                                    if msg.get("method") == "ping":
                                        await self._handle_ping(msg)
                                        continue
                                    
                                    # 일반 응답 처리
                                    if "id" in msg:
                                        await self._handle_response(msg)
                                    else:
                                        # Notification (ID 없음)
                                        logger.debug(
                                            f"[SSE] Notification: "
                                            f"{msg.get('method')}"
                                        )

                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"[SSE] JSON 파싱 실패: {e}, "
                                        f"data={data_str[:100]}"
                                    )

            except asyncio.TimeoutError:
                logger.warning("[SSE Listener] ⏱️  타임아웃 - 재연결 필요")
                
            except Exception as e:
                logger.error(f"[SSE Listener] 오류: {e}", exc_info=True)
                
            finally:
                # SSE 클라이언트 정리
                if self.sse_client:
                    await self.sse_client.aclose()
                    self.sse_client = None

            # 재연결 로직
            if self.running and self.auto_reconnect:
                self.reconnect_attempts += 1
                
                # 지수 백오프 (최대 60초)
                delay = min(
                    self.base_reconnect_delay * (2 ** self.reconnect_attempts),
                    self.max_reconnect_delay
                )
                
                logger.warning(
                    f"[SSE Listener] {delay:.1f}초 후 재연결 시도... "
                    f"(시도 #{self.reconnect_attempts})"
                )
                
                await asyncio.sleep(delay)
                
                # 세션 ID는 유지 (서버가 인식할 수 있음)
                # 새로운 세션이 필요하면 서버가 새 ID를 줄 것
                logger.info("[SSE Listener] 재연결 시작 (세션 유지 시도)")
            else:
                logger.info("[SSE Listener] 재연결 비활성화 - 종료")
                break

        logger.info("[SSE Listener] 종료")

    async def _handle_ping(self, ping_msg: Dict[str, Any]):
        """
        Ping 메시지 처리
        
        JSON-RPC 2.0 형식:
        요청: {"jsonrpc": "2.0", "id": 123, "method": "ping"}
        응답: {"jsonrpc": "2.0", "id": 123, "result": {}}
        """
        ping_id = ping_msg.get("id")
        
        if ping_id is None:
            logger.warning("[Ping] ID 없는 ping - JSON-RPC 표준 위반")
            return
        
        logger.info(f"[Ping] 🏓 수신 (ID={ping_id})")
        self.stats["pings_received"] += 1
        
        # JSON-RPC 2.0 표준 pong 응답 생성
        pong_response = self._create_jsonrpc_response(ping_id, result={})
        
        # 큐에 추가 (논블로킹)
        try:
            self.pong_queue.put_nowait(pong_response)
            logger.debug(
                f"[Ping] Pong 큐 추가 완료 (큐 크기: {self.pong_queue.qsize()})"
            )
        except asyncio.QueueFull:
            logger.error("[Ping] ⚠️  Pong 큐 가득 찼")

    async def _handle_response(self, response_msg: Dict[str, Any]):
        """
        JSON-RPC 응답 처리
        
        Args:
            response_msg: JSON-RPC 2.0 형식의 응답
        """
        msg_id = response_msg.get("id")
        
        if msg_id is None:
            logger.warning("[Response] ID 없는 응답 무시")
            return
        
        logger.debug(
            f"[Response] 수신 (ID={msg_id}), "
            f"대기 중: {list(self.pending_requests.keys())}"
        )
        
        if msg_id in self.pending_requests:
            future = self.pending_requests.pop(msg_id)
            
            if "error" in response_msg:
                error = response_msg["error"]
                logger.error(f"[Response] 에러 (ID={msg_id}): {error}")
                future.set_exception(
                    Exception(f"JSON-RPC Error: {error}")
                )
            else:
                result = response_msg.get("result", {})
                logger.info(f"[Response] 성공 (ID={msg_id})")
                future.set_result(result)
        else:
            logger.warning(
                f"[Response] 매칭 실패 (ID={msg_id}) - "
                f"이미 처리되었거나 타임아웃됨"
            )

    async def _connection_monitor(self):
        """연결 상태 모니터링 (헬스체크 + 태스크 관리)"""
        logger.info("[Monitor] 시작")

        while self.running:
            await asyncio.sleep(self.health_check_interval)

            if not self.running:
                break

            # SSE 리스너 상태 확인
            if self.sse_task and self.sse_task.done():
                logger.warning("[Monitor] SSE 리스너 종료됨 - 재시작")
                self.sse_task = asyncio.create_task(self._sse_listener())

            # Pong 워커 상태 확인
            if self.pong_worker_task and self.pong_worker_task.done():
                logger.warning("[Monitor] Pong 워커 종료됨 - 재시작")
                self.pong_worker_task = asyncio.create_task(self._pong_worker())

            # 활동 시간 체크
            try:
                current_time = asyncio.get_running_loop().time()
            except RuntimeError:
                import time
                current_time = time.time()

            if self.last_activity > 0:
                idle_time = current_time - self.last_activity
                
                if idle_time > self.idle_timeout:
                    logger.warning(
                        f"[Monitor] ⚠️  {int(idle_time)}초 동안 활동 없음"
                    )

            # Pong 큐 상태
            queue_size = self.pong_queue.qsize()
            if queue_size > 5:
                logger.warning(f"[Monitor] Pong 큐 밀림: {queue_size}개 대기")

            # 통계 로깅 (디버그 모드)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[Monitor] 통계 - "
                    f"재연결: {self.stats['total_reconnects']}, "
                    f"Ping/Pong: {self.stats['pings_received']}/{self.stats['pongs_sent']}, "
                    f"실패: {self.stats['pongs_failed']}, "
                    f"메시지: {self.stats['messages_sent']}/{self.stats['messages_received']}"
                )

        logger.info("[Monitor] 종료")

    async def initialize(self) -> Dict[str, Any]:
        """
        MCP 서버 초기화
        
        1. SSE 연결 수립
        2. 세션 ID 획득
        3. initialize 요청
        4. initialized 알림
        
        Returns:
            초기화 결과 (서버 capabilities 등)
        """
        logger.info("[Initialize] 시작...")

        # 기존 연결 정리
        if self.sse_task and not self.sse_task.done():
            logger.info("[Initialize] 기존 SSE 리스너 종료 중...")
            self.running = False
            try:
                await asyncio.wait_for(self.sse_task, timeout=2.0)
            except asyncio.TimeoutError:
                self.sse_task.cancel()

        if self.pong_worker_task and not self.pong_worker_task.done():
            logger.info("[Initialize] 기존 Pong 워커 종료 중...")
            try:
                await asyncio.wait_for(self.pong_worker_task, timeout=2.0)
            except asyncio.TimeoutError:
                self.pong_worker_task.cancel()

        # 초기화
        self.reconnect_attempts = 0
        self.session_id = None
        self.is_initialized = False
        self.stats["uptime_start"] = datetime.now()

        # 🔥 이전 세션의 stale pong 메시지 제거
        if not self.pong_queue.empty():
            old_queue_size = self.pong_queue.qsize()
            logger.warning(
                f"[Initialize] 이전 세션의 {old_queue_size}개 pong 메시지 정리 중..."
            )
            while not self.pong_queue.empty():
                try:
                    self.pong_queue.get_nowait()
                    self.pong_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            logger.info("[Initialize] ✓ Pong 큐 정리 완료")

        # 🔥 Pending requests도 정리 (타임아웃된 요청들)
        if self.pending_requests:
            logger.warning(
                f"[Initialize] 이전 세션의 {len(self.pending_requests)}개 요청 정리 중..."
            )
            for req_id, future in list(self.pending_requests.items()):
                if not future.done():
                    future.set_exception(Exception("Session reset"))
            self.pending_requests.clear()
            logger.info("[Initialize] ✓ Pending requests 정리 완료")

        # Request ID 카운터 초기화 (새 세션은 1부터 시작)
        self.request_id = 0
        logger.info("[Initialize] ✓ Request ID 카운터 초기화")

        # 백그라운드 태스크 시작
        self.running = True
        
        # Pong 워커 시작
        self.pong_worker_task = asyncio.create_task(self._pong_worker())
        logger.info("[Initialize] ✓ Pong 워커 시작")
        
        # SSE 리스너 시작
        self.sse_task = asyncio.create_task(self._sse_listener())
        logger.info("[Initialize] ✓ SSE 리스너 시작")

        # 연결 모니터 시작
        if not self.monitor_task or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self._connection_monitor())
            logger.info("[Initialize] ✓ 모니터 시작")

        # 세션 ID 획득 대기 (최대 15초)
        logger.info("[Initialize] 세션 ID 대기 중...")
        for i in range(150):  # 0.1초 × 150 = 15초
            if self.session_id:
                break
            await asyncio.sleep(0.1)

        if not self.session_id:
            raise Exception("세션 ID 획득 실패 (15초 타임아웃)")

        logger.info(f"[Initialize] ✓ 세션 ID: {self.session_id}")

        # initialize 요청 전송 (JSON-RPC 2.0)
        request = self._create_jsonrpc_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "hooxi-carbon-ai",
                    "version": "1.0.0"
                }
            },
            request_id=self._next_id()
        )

        result = await self._send_request(request)
        logger.info("[Initialize] ✓ 서버 초기화 완료")

        # initialized 알림 전송 (JSON-RPC 2.0 notification)
        notification = self._create_jsonrpc_request(
            method="notifications/initialized",
            params=None,
            request_id=None  # Notification은 ID 없음
        )

        logger.info("[Initialize] initialized 알림 전송...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{self.base_url}/mcp/message?sessionId={self.session_id}"

            response = await client.post(
                url,
                json=notification,
                headers=self._get_headers()
            )

            if response.status_code != 200:
                logger.warning(
                    f"[Initialize] initialized 알림 실패: {response.status_code}"
                )
            else:
                logger.info("[Initialize] ✓ initialized 알림 완료")

        self.is_initialized = True
        logger.info("[Initialize] ✅ 초기화 완료")
        
        return result

    async def list_tools(self) -> list[Dict[str, Any]]:
        """도구 목록 조회"""
        logger.info("[Tools] 목록 조회 중...")

        if not self.is_initialized:
            await self.initialize()

        request = self._create_jsonrpc_request(
            method="tools/list",
            params={},
            request_id=self._next_id()
        )

        result = await self._send_request(request)
        tools = result.get("tools", [])
        
        logger.info(f"[Tools] {len(tools)}개 도구 발견")
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """도구 호출"""
        logger.info(f"[Tool Call] {tool_name}")

        if not self.is_initialized:
            await self.initialize()

        request = self._create_jsonrpc_request(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            },
            request_id=self._next_id()
        )

        result = await self._send_request(request, timeout=timeout)
        logger.info(f"[Tool Call] ✓ {tool_name} 완료")
        
        return result

    async def _send_request(
        self,
        request: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        JSON-RPC 요청 전송 및 응답 대기
        
        Args:
            request: JSON-RPC 2.0 형식의 요청
            timeout: 응답 대기 시간 (초)
            
        Returns:
            응답 결과
            
        Raises:
            Exception: 요청 실패 또는 타임아웃
        """
        req_id = request.get("id")
        method = request.get("method", "unknown")

        logger.info(f"[Request] 전송: ID={req_id}, method={method}")

        # SSE 리스너 상태 확인
        if not self.running or not self.sse_task or self.sse_task.done():
            logger.warning("[Request] SSE 리스너 재시작 중...")
            self.running = True
            self.sse_task = asyncio.create_task(self._sse_listener())
            await asyncio.sleep(1.0)

        # 세션 ID 확인
        if not self.session_id:
            raise Exception("세션 ID 없음 - 초기화 필요")

        # Future 생성
        future = asyncio.Future()
        self.pending_requests[req_id] = future
        
        logger.debug(
            f"[Request] Future 등록: ID={req_id}, "
            f"대기 중: {list(self.pending_requests.keys())}"
        )

        try:
            # POST 요청 전송
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/mcp/message?sessionId={self.session_id}"
                
                logger.debug(f"[Request] POST: {url}")

                response = await client.post(
                    url,
                    json=request,
                    headers=self._get_headers()
                )

                logger.info(f"[Request] POST 응답: {response.status_code}")
                self.stats["messages_sent"] += 1

                if response.status_code != 200:
                    raise Exception(
                        f"Request failed: {response.status_code} - {response.text}"
                    )

            # SSE로 응답 대기
            logger.info(f"[Request] SSE 응답 대기 (timeout={timeout}초)...")
            result = await asyncio.wait_for(future, timeout=timeout)
            
            logger.info(f"[Request] ✓ 응답 수신: ID={req_id}")
            return result

        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            logger.error(
                f"[Request] ⏱️  타임아웃: ID={req_id}, method={method}"
            )
            raise Exception(f"Request timeout (ID={req_id}, method={method})")
            
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            logger.error(f"[Request] ❌ 실패: ID={req_id}, error={e}")
            raise

    async def close(self):
        """연결 종료 및 정리"""
        logger.info("[Close] 종료 중...")
        self.running = False

        # SSE 리스너 종료
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass

        # Pong 워커 종료
        if self.pong_worker_task:
            self.pong_worker_task.cancel()
            try:
                await self.pong_worker_task
            except asyncio.CancelledError:
                pass

        # 모니터 종료
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        # SSE 클라이언트 정리
        if self.sse_client:
            await self.sse_client.aclose()

        # 대기 중인 요청 취소
        for req_id, future in self.pending_requests.items():
            if not future.done():
                future.set_exception(Exception("MCP client closed"))
        self.pending_requests.clear()

        logger.info("[Close] ✓ 종료 완료")

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        stats = self.stats.copy()
        
        if stats["uptime_start"]:
            uptime = datetime.now() - stats["uptime_start"]
            stats["uptime_seconds"] = uptime.total_seconds()
        
        return stats

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 사용 예제
async def example_usage():
    """SSE MCP 클라이언트 사용 예제"""
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    async with SSEMCPClient(
        base_url="https://hooxi.shinssy.com",
        auto_reconnect=True
    ) as client:
        
        # 도구 목록 조회
        tools = await client.list_tools()
        print(f"\n✅ 발견된 도구: {len(tools)}개")

        for tool in tools[:3]:
            print(f"  - {tool['name']}: {tool.get('description', '')[:60]}")

        # 도구 호출 예제
        if tools:
            print(f"\n🔧 첫 번째 도구 호출 중...")
            result = await client.call_tool(tools[0]['name'], {})
            print(f"✅ 결과: {result}")
        
        # 장시간 연결 유지 테스트 (재연결 확인)
        print("\n⏳ 5분 동안 연결 유지 테스트 (강제 종료 시 자동 재연결)...")
        print("   Ctrl+C로 종료하거나, 서버 연결을 끊어보세요!")
        
        for i in range(30):  # 30 × 10초 = 5분
            await asyncio.sleep(10)
            
            # 통계 출력
            stats = client.get_stats()
            print(
                f"[{i+1}/30] "
                f"재연결: {stats['total_reconnects']}번, "
                f"Ping: {stats['pings_received']}개, "
                f"Pong: {stats['pongs_sent']}개 "
                f"(실패: {stats['pongs_failed']}개)"
            )
            
            # 간단한 도구 호출로 연결 확인
            try:
                await client.list_tools()
                print(f"    ✓ 연결 정상")
            except Exception as e:
                print(f"    ⚠️  연결 문제: {e}")
        
        print("\n✅ 5분 테스트 완료!")
        
        # 최종 통계
        final_stats = client.get_stats()
        print("\n📊 최종 통계:")
        print(f"  - 총 재연결: {final_stats['total_reconnects']}번")
        print(f"  - Ping 수신: {final_stats['pings_received']}개")
        print(f"  - Pong 전송: {final_stats['pongs_sent']}개 (실패: {final_stats['pongs_failed']}개)")
        print(f"  - 메시지 송신: {final_stats['messages_sent']}개")
        print(f"  - 메시지 수신: {final_stats['messages_received']}개")
        print(f"  - 업타임: {final_stats.get('uptime_seconds', 0):.1f}초")


if __name__ == "__main__":
    try:
        asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\n\n👋 사용자 종료")