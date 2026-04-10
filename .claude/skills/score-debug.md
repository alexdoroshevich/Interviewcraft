# /score-debug — Debug a session's scoring state

Diagnoses why a session's scores are missing, incorrect, or not reflected in the skill graph.
Pass the session ID as an argument: `/score-debug <session-id>`

## Steps

### 1. Check backend logs for scoring events
```bash
docker compose logs backend --tail=500 2>&1 | grep "$ARGUMENTS" | grep -iE "(scoring|segment|skill|story|error|exception)" | tail -30
```

### 2. Fetch session status and scoring result
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
  SELECT
    id,
    status,
    type,
    quality_profile,
    jsonb_array_length(transcript) AS transcript_turns,
    scoring_result IS NOT NULL AS has_scoring_result,
    scoring_result->'overall_score' AS overall_score,
    scoring_result->'segments_scored' AS segments_scored
  FROM sessions
  WHERE id = '$ARGUMENTS'
  LIMIT 1;
" 2>&1
```

### 3. Fetch per-segment scores
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
  SELECT
    id,
    segment_index,
    score,
    jsonb_array_length(evidence) AS evidence_count,
    jsonb_array_length(lint_results) AS lint_flags
  FROM session_segments
  WHERE session_id = '$ARGUMENTS'
  ORDER BY segment_index;
" 2>&1
```

### 4. Check skill graph was updated (look up user_id first)
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
  SELECT sn.skill_name, sn.current_score, sn.trend,
         sh.score AS last_recorded_score, sh.recorded_at
  FROM skill_nodes sn
  JOIN skill_history sh ON sh.skill_node_id = sn.id
  WHERE sn.user_id = (SELECT user_id FROM sessions WHERE id = '$ARGUMENTS')
  ORDER BY sh.recorded_at DESC
  LIMIT 20;
" 2>&1
```

### 5. Check API cost was logged (confirms Anthropic call was made)
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
  SELECT operation, input_tokens, output_tokens, cost_usd, cached, latency_ms, created_at
  FROM usage_logs
  WHERE user_id = (SELECT user_id FROM sessions WHERE id = '$ARGUMENTS')
    AND created_at > NOW() - INTERVAL '2 hours'
  ORDER BY created_at DESC
  LIMIT 10;
" 2>&1
```

### 6. Summarize

Based on the output above, diagnose:
- **No scoring_result**: scoring job never ran or Anthropic call failed — check logs for errors, verify API key is set
- **scoring_result exists but no skill_history rows**: skill graph update failed — check for skill_graph errors in logs
- **score is 0 on all segments**: empty answer or transcript parse failure — check transcript_turns count
- **usage_logs empty**: API call never completed — check provider connectivity and BYOK key validity
