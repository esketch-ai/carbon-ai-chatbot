pipeline {
    agent any

    environment {
        // Docker 이미지 설정
        DOCKER_REGISTRY = credentials('docker-registry-url')  // Jenkins에서 설정
        IMAGE_TAG = "${BUILD_NUMBER}"

        // GitHub 저장소
        GIT_REPO = 'https://github.com/esketch-ai/carbon-ai-chatbot.git'
        GIT_BRANCH = 'main'

        // 배포 경로 (Synology NAS)
        DEPLOY_PATH = '/volume1/docker/carbon-ai-chatbot'

        // Docker Compose 프로젝트명
        COMPOSE_PROJECT_NAME = 'carbonai'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${GIT_BRANCH}"]],
                    userRemoteConfigs: [[
                        url: "${GIT_REPO}",
                        credentialsId: 'github-credentials'
                    ]]
                ])

                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Lint & Type Check') {
            parallel {
                stage('Backend Lint') {
                    steps {
                        dir('react-agent') {
                            sh '''
                                python -m pip install ruff --quiet
                                ruff check src/ || true
                            '''
                        }
                    }
                }
                stage('Frontend Lint') {
                    steps {
                        dir('agent-chat-ui') {
                            sh '''
                                npm install -g pnpm
                                pnpm install --frozen-lockfile
                                pnpm run lint || true
                            '''
                        }
                    }
                }
            }
        }

        stage('Build Docker Images') {
            parallel {
                stage('Build Backend') {
                    steps {
                        script {
                            docker.build(
                                "carbonai-backend:${IMAGE_TAG}",
                                "-f Dockerfile ."
                            )
                        }
                    }
                }
                stage('Build Frontend') {
                    steps {
                        script {
                            docker.build(
                                "carbonai-frontend:${IMAGE_TAG}",
                                "--build-arg NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} " +
                                "-f agent-chat-ui/Dockerfile ./agent-chat-ui"
                            )
                        }
                    }
                }
            }
        }

        stage('Test') {
            steps {
                dir('react-agent') {
                    sh '''
                        python -m pip install -e ".[dev]" --quiet
                        python -m pytest tests/unit_tests/ -v --tb=short || true
                    '''
                }
            }
        }

        stage('Deploy to NAS') {
            when {
                branch 'main'
            }
            steps {
                script {
                    // 환경 변수 파일 복사
                    sh """
                        cp .env.production ${DEPLOY_PATH}/.env 2>/dev/null || true
                    """

                    // Docker 이미지 태그
                    sh """
                        docker tag carbonai-backend:${IMAGE_TAG} carbonai-backend:latest
                        docker tag carbonai-frontend:${IMAGE_TAG} carbonai-frontend:latest
                    """

                    // Docker Compose 배포
                    dir("${DEPLOY_PATH}") {
                        sh """
                            docker-compose down --remove-orphans || true
                            docker-compose up -d --force-recreate
                        """
                    }
                }
            }
        }

        stage('Health Check') {
            when {
                branch 'main'
            }
            steps {
                script {
                    // 서비스 시작 대기
                    sleep(time: 30, unit: 'SECONDS')

                    // 헬스체크
                    sh '''
                        curl -f http://localhost:7860/ok || exit 1
                        curl -f http://localhost:3000 || exit 1
                    '''
                }
            }
        }

        stage('Cleanup') {
            steps {
                // 오래된 Docker 이미지 정리
                sh '''
                    docker image prune -f --filter "until=168h"
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Build #${BUILD_NUMBER} succeeded!"
            // 슬랙/이메일 알림 (선택)
            // slackSend(color: 'good', message: "Build succeeded: ${env.JOB_NAME} #${BUILD_NUMBER}")
        }
        failure {
            echo "❌ Build #${BUILD_NUMBER} failed!"
            // slackSend(color: 'danger', message: "Build failed: ${env.JOB_NAME} #${BUILD_NUMBER}")
        }
        always {
            // 워크스페이스 정리
            cleanWs()
        }
    }
}
