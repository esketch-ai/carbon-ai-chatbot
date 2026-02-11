"""Pipeline scheduler module for automated weekly analysis.

This module provides APScheduler-based scheduling for automatic
execution of the weekly analysis pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .pipeline import PipelineResult, WeeklyPipeline


@dataclass
class SchedulerConfig:
    """Configuration for the pipeline scheduler.

    Attributes:
        day_of_week: Day of week to run (mon, tue, wed, thu, fri, sat, sun).
        hour: Hour of day to run (0-23).
        minute: Minute of hour to run (0-59).
        timezone: Timezone for scheduling (e.g., 'Asia/Seoul', 'UTC').
    """

    day_of_week: str = "mon"
    hour: int = 0
    minute: int = 0
    timezone: str = "Asia/Seoul"


class PipelineScheduler:
    """Scheduler for automated pipeline execution.

    Uses APScheduler to schedule and manage automatic execution
    of the weekly analysis pipeline.

    Attributes:
        config: The scheduler configuration.
    """

    def __init__(
        self,
        config: Optional[SchedulerConfig] = None,
        on_complete: Optional[Callable[[PipelineResult], None]] = None,
    ) -> None:
        """Initialize the PipelineScheduler.

        Args:
            config: Scheduler configuration. Uses defaults if None.
            on_complete: Optional callback function called when pipeline completes.
                        Receives the PipelineResult as argument.
        """
        self.config = config or SchedulerConfig()
        self._on_complete = on_complete
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._pipeline: Optional[WeeklyPipeline] = None

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running.

        Returns:
            True if the scheduler is running, False otherwise.
        """
        if self._scheduler is None:
            return False
        return self._scheduler.running

    @property
    def next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time.

        Returns:
            The next scheduled run time, or None if not scheduled.
        """
        if self._scheduler is None or not self._scheduler.running:
            return None

        job = self._scheduler.get_job("weekly_pipeline")
        if job is None:
            return None

        return job.next_run_time

    def start(self) -> None:
        """Start the scheduler.

        Creates and starts the APScheduler with the configured trigger.
        The pipeline will run automatically at the scheduled time.
        """
        if self._scheduler is not None and self._scheduler.running:
            return

        self._scheduler = AsyncIOScheduler(timezone=self.config.timezone)

        # Create cron trigger
        trigger = CronTrigger(
            day_of_week=self.config.day_of_week,
            hour=self.config.hour,
            minute=self.config.minute,
            timezone=self.config.timezone,
        )

        # Add job
        self._scheduler.add_job(
            self._run_pipeline,
            trigger=trigger,
            id="weekly_pipeline",
            name="Weekly Analysis Pipeline",
            replace_existing=True,
        )

        self._scheduler.start()

    def stop(self) -> None:
        """Stop the scheduler.

        Gracefully shuts down the scheduler. Any running job
        will complete before shutdown.
        """
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            self._scheduler = None

    async def run_now(self) -> PipelineResult:
        """Run the pipeline immediately.

        Executes the pipeline without waiting for the scheduled time.
        Useful for testing or manual runs.

        Returns:
            PipelineResult containing the pipeline execution results.
        """
        return await self._run_pipeline()

    async def _run_pipeline(self) -> PipelineResult:
        """Execute the pipeline.

        Internal method that runs the actual pipeline and handles
        the completion callback.

        Returns:
            PipelineResult containing the pipeline execution results.
        """
        # Create pipeline instance
        if self._pipeline is None:
            self._pipeline = WeeklyPipeline()

        # Run the pipeline
        result = await self._pipeline.run()

        # Call completion callback if provided
        if self._on_complete is not None:
            try:
                self._on_complete(result)
            except Exception:
                # Don't let callback errors affect the result
                pass

        return result
