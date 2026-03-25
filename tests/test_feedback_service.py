"""
Unit tests for FeedbackService.
"""
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import User, Department, Task, Assignment, Feedback, FeedbackType, AssignmentStatus, TaskStatus
from app.schemas.feedback import FeedbackCreate
from app.services.feedback_service import FeedbackService


class TestFeedbackService:
    """Tests for FeedbackService."""

    @pytest.fixture
    async def setup_data(self, async_db_session):
        """Setup test data."""
        # Create departments
        dept1 = Department(id=1, name="Lead Dept", leader_id=1)
        dept2 = Department(id=2, name="Collab Dept", leader_id=2)
        async_db_session.add_all([dept1, dept2])

        # Create users
        user1 = User(id=1, name="Leader User", email="leader@example.com", role="leader", dept_id=1)
        user2 = User(id=2, name="Collab User", email="collab@example.com", role="dept_head", dept_id=2)
        async_db_session.add_all([user1, user2])

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

        # Create assignment
        assignment = Assignment(
            id=1,
            task_id=1,
            dept_id=2,
            status=AssignmentStatus.PENDING
        )
        async_db_session.add(assignment)

        await async_db_session.flush()

        return {"task": task, "assignment": assignment, "user1": user1, "user2": user2}

    @pytest.mark.asyncio
    async def test_create_feedback_agree(self, async_db_session, setup_data):
        """Test creating feedback with 'agree' type."""
        service = FeedbackService(async_db_session)

        feedback_data = FeedbackCreate(
            assignment_id=1,
            feedback_type=FeedbackType.AGREE,
            reason="Looks good to me"
        )

        feedback = await service.create_feedback(1, feedback_data, setup_data["user2"])

        assert feedback.id is not None
        assert feedback.feedback_type == FeedbackType.AGREE
        assert feedback.reason == "Looks good to me"
        assert feedback.dept_id == 2

        # Check assignment status updated
        result = await async_db_session.execute(select(Assignment).where(Assignment.id == 1))
        assignment = result.scalar_one()
        assert assignment.status == AssignmentStatus.AGREED

    @pytest.mark.asyncio
    async def test_create_feedback_disagree(self, async_db_session, setup_data):
        """Test creating feedback with 'disagree' type."""
        service = FeedbackService(async_db_session)

        feedback_data = FeedbackCreate(
            assignment_id=1,
            feedback_type=FeedbackType.DISAGREE,
            reason="I have concerns",
            proposed_changes={"field": "deadline", "value": "2024-12-31"}
        )

        feedback = await service.create_feedback(1, feedback_data, setup_data["user2"])

        assert feedback.id is not None
        assert feedback.feedback_type == FeedbackType.DISAGREE
        assert feedback.proposed_changes is not None

        # Check assignment status updated to disputed
        result = await async_db_session.execute(select(Assignment).where(Assignment.id == 1))
        assignment = result.scalar_one()
        assert assignment.status == AssignmentStatus.DISPUTED

    @pytest.mark.asyncio
    async def test_create_feedback_need_discussion(self, async_db_session, setup_data):
        """Test creating feedback with 'need_discussion' type."""
        service = FeedbackService(async_db_session)

        feedback_data = FeedbackCreate(
            assignment_id=1,
            feedback_type=FeedbackType.NEED_DISCUSSION,
            reason="Need to discuss with team"
        )

        feedback = await service.create_feedback(1, feedback_data, setup_data["user2"])

        assert feedback.id is not None
        assert feedback.feedback_type == FeedbackType.NEED_DISCUSSION

    @pytest.mark.asyncio
    async def test_create_feedback_wrong_department(self, async_db_session, setup_data):
        """Test that wrong department cannot submit feedback."""
        from app.core.exceptions import ForbiddenException

        service = FeedbackService(async_db_session)

        feedback_data = FeedbackCreate(
            assignment_id=1,
            feedback_type=FeedbackType.AGREE,
            reason="Test"
        )

        # user1 is from lead department, not the assigned department
        with pytest.raises(ForbiddenException):
            await service.create_feedback(1, feedback_data, setup_data["user1"])

    @pytest.mark.asyncio
    async def test_get_feedback_by_id(self, async_db_session, setup_data):
        """Test getting feedback by ID."""
        service = FeedbackService(async_db_session)

        # Create a feedback first
        feedback_data = FeedbackCreate(
            assignment_id=1,
            feedback_type=FeedbackType.AGREE,
            reason="Test feedback"
        )
        created = await service.create_feedback(1, feedback_data, setup_data["user2"])

        # Get it back
        result = await service.get_feedback_by_id(created.id, setup_data["user2"])

        assert result.id == created.id
        assert result.reason == "Test feedback"

    @pytest.mark.asyncio
    async def test_get_assignment_feedbacks(self, async_db_session, setup_data):
        """Test getting feedbacks for an assignment."""
        service = FeedbackService(async_db_session)

        # Create multiple feedbacks
        for i, feedback_type in enumerate([FeedbackType.AGREE, FeedbackType.DISAGREE, FeedbackType.NEED_DISCUSSION]):
            feedback_data = FeedbackCreate(
                assignment_id=1,
                feedback_type=feedback_type,
                reason=f"Feedback {i}"
            )
            await service.create_feedback(1, feedback_data, setup_data["user2"])

        # Get feedbacks
        feedbacks, total = await service.get_assignment_feedbacks(1, setup_data["user2"])

        assert total == 3
        assert len(feedbacks) == 3
