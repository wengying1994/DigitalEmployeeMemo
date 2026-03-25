"""
Unit tests for ConflictService.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import User, Department, Task, Memo, MemoType, MemoStatus, ConflictReport, ConflictStatus, TaskStatus
from app.schemas.conflict import ConflictCreate, ConflictDecision
from app.services.conflict_service import ConflictService


class TestConflictService:
    """Tests for ConflictService."""

    @pytest.fixture
    async def setup_data(self, async_db_session):
        """Setup test data."""
        # Create department
        dept1 = Department(id=1, name="Lead Dept", leader_id=1)
        dept2 = Department(id=2, name="Collab Dept", leader_id=2)
        async_db_session.add_all([dept1, dept2])

        # Create users
        leader = User(id=1, name="Leader User", email="leader@example.com", role="leader", dept_id=1)
        reporter = User(id=3, name="Reporter User", email="reporter@example.com", role="dept_head", dept_id=1)
        async_db_session.add_all([leader, reporter])

        # Create task
        task = Task(
            id=1,
            title="Test Task",
            description="Test description",
            lead_dept_id=1,
            created_by=1,
            status=TaskStatus.COORDINATING
        )
        async_db_session.add(task)

        await async_db_session.flush()

        return {"task": task, "leader": leader, "reporter": reporter}

    @pytest.mark.asyncio
    async def test_create_conflict_report(self, async_db_session, setup_data):
        """Test creating a conflict report."""
        service = ConflictService(async_db_session)

        conflict_data = ConflictCreate(
            task_id=1,
            conflict_summary="Resource allocation conflict",
            conflict_details={"resource": "budget", "issue": "insufficient"},
            proposed_solutions=[
                {"id": 1, "description": "Increase budget"},
                {"id": 2, "description": "Reduce scope"}
            ],
            urgency_level="high",
            need_decision_by=datetime.utcnow() + timedelta(days=2)
        )

        conflict = await service.create_conflict(conflict_data, setup_data["reporter"])

        assert conflict.id is not None
        assert conflict.conflict_summary == "Resource allocation conflict"
        assert conflict.urgency_level == "high"
        assert conflict.status == ConflictStatus.PENDING
        assert conflict.reporter_user_id == setup_data["reporter"].id
        assert conflict.reporter_dept_id == setup_data["reporter"].dept_id

    @pytest.mark.asyncio
    async def test_create_conflict_generates_memo(self, async_db_session, setup_data):
        """Test that creating a conflict generates a memo for the leader."""
        service = ConflictService(async_db_session)

        conflict_data = ConflictCreate(
            task_id=1,
            conflict_summary="Test conflict",
            conflict_details={"description": "Test"},
            urgency_level="medium"
        )

        conflict = await service.create_conflict(conflict_data, setup_data["reporter"])

        # Check memo was created
        result = await async_db_session.execute(
            select(Memo).where(Memo.related_id == conflict.id)
        )
        memo = result.scalar_one_or_none()

        assert memo is not None
        assert memo.user_id == setup_data["leader"].id  # Memo sent to leader
        assert memo.memo_type == MemoType.CONFLICT
        assert memo.status == MemoStatus.UNREAD
        assert conflict.memo_id == memo.id

    @pytest.mark.asyncio
    async def test_resolve_conflict(self, async_db_session, setup_data):
        """Test resolving a conflict."""
        service = ConflictService(async_db_session)

        # Create conflict first
        conflict_data = ConflictCreate(
            task_id=1,
            conflict_summary="Test conflict",
            conflict_details={"description": "Test"},
            urgency_level="medium"
        )
        conflict = await service.create_conflict(conflict_data, setup_data["reporter"])

        # Resolve as leader
        decision = ConflictDecision(
            decision_content="Approved solution 1",
            notify_departments=[2]
        )

        resolved = await service.resolve_conflict(conflict.id, decision, setup_data["leader"])

        assert resolved.status == ConflictStatus.RESOLVED
        assert resolved.decision_content == "Approved solution 1"
        assert resolved.decision_maker_id == setup_data["leader"].id
        assert resolved.decision_made_at is not None

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_conflict(self, async_db_session, setup_data):
        """Test that resolving an already resolved conflict fails."""
        from app.core.exceptions import ConflictAlreadyResolvedException

        service = ConflictService(async_db_session)

        # Create and resolve conflict
        conflict_data = ConflictCreate(
            task_id=1,
            conflict_summary="Test conflict",
            conflict_details={"description": "Test"},
            urgency_level="medium"
        )
        conflict = await service.create_conflict(conflict_data, setup_data["reporter"])

        decision = ConflictDecision(decision_content="First decision")
        await service.resolve_conflict(conflict.id, decision, setup_data["leader"])

        # Try to resolve again
        with pytest.raises(ConflictAlreadyResolvedException):
            await service.resolve_conflict(conflict.id, decision, setup_data["leader"])

    @pytest.mark.asyncio
    async def test_get_conflicts_with_filters(self, async_db_session, setup_data):
        """Test getting conflicts with filters."""
        service = ConflictService(async_db_session)

        # Create multiple conflicts
        for i, urgency in enumerate(["low", "medium", "high", "critical"]):
            conflict_data = ConflictCreate(
                task_id=1,
                conflict_summary=f"Conflict {i}",
                conflict_details={"description": f"Test {i}"},
                urgency_level=urgency
            )
            await service.create_conflict(conflict_data, setup_data["reporter"])

        # Get only high+urgency conflicts
        conflicts, total = await service.get_conflicts(
            setup_data["leader"],
            urgency_level="high"
        )

        assert total == 2  # Only high and critical

    @pytest.mark.asyncio
    async def test_escalate_conflict(self, async_db_session, setup_data):
        """Test escalating a conflict."""
        service = ConflictService(async_db_session)

        conflict_data = ConflictCreate(
            task_id=1,
            conflict_summary="Test conflict",
            conflict_details={"description": "Test"},
            urgency_level="medium"
        )
        conflict = await service.create_conflict(conflict_data, setup_data["reporter"])

        escalated = await service.escalate_conflict(conflict.id, setup_data["reporter"])

        assert escalated.status == ConflictStatus.ESCALATED
