# Create Langfuse Annotation Queue

## Background

Langfuse v3 does not provide a public API for creating annotation queues.
They must be created manually via the UI.

## Steps to Create Queue

### 1. Open Langfuse UI
Navigate to: http://localhost:3000

### 2. Go to Annotation Queues
- Click on project: **SkillForge Backend**
- Navigate to: **Settings** → **Annotation Queues**
- Or direct link: http://localhost:3000/project/skillforge/annotation-queues

### 3. Create New Queue
Click **"Create Queue"** button

### 4. Fill in Queue Details
- **Name**: `SkillForge Review Queue`
- **Description**: `Queue for human review of SkillForge analysis artifacts`
- **Score Configs** (optional): Select relevant scores for review
  - `user_feedback` (BOOLEAN) - Thumbs up/down
  - `g_eval_overall` (NUMERIC) - Overall quality score

### 5. Save Queue
Click **"Create"** or **"Save"**

### 6. Copy Queue ID
After creation, copy the queue ID from the URL or queue details page.

Example queue ID format: `cmjctaben004xqn07msf77nqy`

### 7. Update Backend .env
Add or update the queue ID in `backend/.env`:

```bash
# Langfuse Annotation Queue (auto-configured)
LANGFUSE_ANNOTATION_QUEUE_ID=<your-new-queue-id>
```

### 8. Verify Setup
Run the verification script:

```bash
cd backend
poetry run python scripts/setup_langfuse_annotation_queue.py
```

Expected output:
```
✓ Found queue ID: <your-queue-id>
✓ Added LANGFUSE_ANNOTATION_QUEUE_ID to .env
```

## Using the Annotation Queue

Once configured, the queue can be used for:

1. **Manual Review Workflow**
   - Backend API submits artifacts to queue
   - Human reviewers access queue via Langfuse UI
   - Reviewers provide feedback and scores

2. **API Integration**
   ```python
   from langfuse import Langfuse

   langfuse = Langfuse()
   queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID")

   # Add item to queue
   langfuse.annotation_queue_item(
       queue_id=queue_id,
       trace_id=trace.id,
       observation_id=observation.id
   )
   ```

3. **View Queue Items**
   - Navigate to: http://localhost:3000/project/skillforge/annotation-queues/<queue-id>
   - Review pending items
   - Submit annotations and scores

## Troubleshooting

### Queue Not Found
- Verify queue name is exactly: `SkillForge Review Queue`
- Check you're in the correct project: `skillforge`
- Ensure you have permissions to create queues

### Queue ID Not Working
- Verify the queue ID matches what's in Langfuse UI
- Restart backend after updating .env
- Check LANGFUSE_ENABLED=true in .env

### API Errors
- Verify LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are correct
- Check Langfuse is running: `curl http://localhost:3000/api/public/health`
- Review Langfuse logs: `docker compose logs langfuse-web`
