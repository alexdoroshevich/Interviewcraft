# /score-debug — Debug a session's scoring state

Checks why a session's scores are missing or incorrect.
Pass the session ID as an argument: `/score-debug <session-id>`

## Steps

1. Check backend logs for scoring events for this session:
```bash
docker compose logs backend --tail=500 2>&1 | grep "$ARGUMENTS" | grep -E "(scoring|segment|skill_graph|story)" | tail -20
```

2. Query the database for session and segment scores:
```bash
docker compose exec postgres psql -U postgres -d interviewcraft -c "
  SELECT id, status, lint_results->>'segments_scored' as segments_scored,
         array_length(transcript, 1) as transcript_turns
  FROM interview_sessions WHERE id = '$ARGUMENTS';
" 2>&1
```

3. Check if skill graph nodes were created:
```bash
docker compose exec postgres psql -U postgres -d interviewcraft -c "
  SELECT skill_name, score, updated_at FROM skill_graph_nodes
  WHERE session_id = '$ARGUMENTS' ORDER BY updated_at DESC;
" 2>&1
```

4. Summarize: what went wrong and what the user should do (re-score, check API keys, etc.)
