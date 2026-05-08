# Sample Test Questions

## Thread T-0001: Storage Vendor Approval

These 7 questions exercise: factual lookup, pronoun resolution, ellipsis, correction, comparison, timeline, and graceful failure.

### 1. Direct factual question
**Q:** What did finance finally approve for the storage vendor?
**Expected citations:** `[msg: m_9b2]`, `[msg: m_9b2, page: 2]`
**Expected answer keywords:** approved, $45,000

### 2. Pronoun resolution
**Q:** ok, and when was that approval sent?
**Expected citations:** `[msg: m_9b2]`
**Expected answer keywords:** May 12, 2001

### 3. Ellipsis + reference to earlier attachment
**Q:** compare it with the draft in the earlier attachment
**Expected citations:** `[msg: m_8f1, page: 1]`, `[msg: m_9b2, page: 2]`
**Expected:** difference between $52,000 (draft) and $45,000 (final), $7,000 reduction

### 4. Pronoun referring back
**Q:** who sent the final approval email?
**Expected citations:** `[msg: m_9b2]`
**Expected:** john.smith@enron.com

### 5. Correction handling
**Q:** actually, I meant the original budget, not the revised one
**Expected citations:** `[msg: m_8f1, page: 1]`
**Expected:** $52,000

### 6. Timeline request
**Q:** show me a timeline of this thread
**Expected:** chronological list with dates and citations for each message

### 7. Graceful failure (info not in thread)
**Q:** what is the vendor's phone number?
**Expected:** "I don't have enough information about this in the thread" + suggestion

---

## Demo Video Walkthrough Sequence

1. Select thread `T-0001` from sidebar
2. Ask Q1 → show answer with both citations + debug panel
3. Ask Q2 (pronoun) → show rewrite in debug
4. Ask Q3 (comparison) → show two PDF citations
5. Ask Q5 (correction) → show context handling
6. Toggle "search outside thread" → ask Q1 again, see broader retrieval
7. Ask Q7 (graceful failure) → show "don't have info" response
8. Open `runs/<timestamp>/trace.jsonl` briefly