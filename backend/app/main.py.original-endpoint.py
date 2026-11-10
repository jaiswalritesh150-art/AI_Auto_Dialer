@app.post("/api/v1/telephony/ai-call/{queue_id}/message")
def ai_call_message(
    queue_id: int,
    request: AIConversationRequest,
    db: Session = Depends(get_db)
):

    # =================================================
    # FIND QUEUE
    # =================================================

    queue_item = (
        db.query(CallQueue)
        .filter(
            CallQueue.id == queue_id
        )
        .first()
    )

    if not queue_item:

        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # =================================================
    # FIND LEAD
    # =================================================

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == queue_item.lead_id
        )
        .first()
    )

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    # =================================================
    # FIND LATEST ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(
            CallAttempt.attempt_number.desc()
        )
        .first()
    )

    if not attempt:

        raise HTTPException(
            status_code=400,
            detail="No call attempt found"
        )

    # =================================================
    # CONVERSATION
    # =================================================

    conversation = list(
        request.conversation
    )

    previous_intelligence = (
        db.query(CallIntelligence)
        .filter(
            CallIntelligence.queue_id == queue_id,
            CallIntelligence.attempt_id == attempt.id
        )
        .order_by(
            CallIntelligence.id.desc()
        )
        .first()
    )

    if (
        previous_intelligence
        and previous_intelligence.transcript
    ):

        previous_lines = (
            previous_intelligence.transcript.split("\n")
        )

        conversation = []

        for line in previous_lines:

            if line.startswith("Lead: "):

                conversation.append({
                    "role": "user",
                    "text": line.replace(
                        "Lead: ",
                        "",
                        1
                    )
                })

            elif line.startswith("AI Agent: "):

                conversation.append({
                    "role": "model",
                    "text": line.replace(
                        "AI Agent: ",
                        "",
                        1
                    )
                })

    conversation.append({
        "role": "user",
        "text": request.message
    })

    # =================================================
    # LEAD CONTEXT
    # =================================================

    lead_context = {
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "company": lead.company,
        "lead_source": lead.lead_source,
        "lead_status": lead.lead_status
    }

    # =================================================
    # GENERATE AI RESPONSE
    # =================================================

    try:

        ai_response = generate_response(
            conversation=conversation,
            lead_context=lead_context
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"AI response failed: {str(exc)}"
        )

    # =================================================
    # ADD AI RESPONSE
    # =================================================

    conversation.append({
        "role": "model",
        "text": ai_response
    })

    # =================================================
    # DETECT CALL DECISION
    # =================================================

    try:

        decision = detect_call_decision(
            conversation=conversation,
            lead_context=lead_context
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Call decision detection failed: "
                f"{str(exc)}"
            )
        )

    decision_type = decision.get(
        "decision",
        "continue"
    )

    # =================================================
    # BUILD TRANSCRIPT
    # =================================================

    transcript_lines = []

    for message in conversation:

        role = message.get(
            "role",
            "user"
        )

        if role == "user":

            speaker = "Lead"

        else:

            speaker = "AI Agent"

        transcript_lines.append(
            f"{speaker}: "
            f"{message.get('text', '')}"
        )

    transcript = "\n".join(
        transcript_lines
    )

    # =================================================
    # PROVISIONAL CALL INTELLIGENCE
    # =================================================

    analysis = {
        "summary": decision.get("reason", "Conversation continued."),
        "sentiment": "neutral",
        "outcome": decision_type
    }
    
    # =================================================
    # SAVE CALL INTELLIGENCE
    # =================================================

    intelligence = CallIntelligence(
        queue_id=queue_id,
        attempt_id=attempt.id,
        transcript=transcript,
        summary=analysis.get("summary"),
        sentiment=analysis.get("sentiment"),
        outcome=analysis.get("outcome")
    )

    db.add(intelligence)

    db.commit()

    db.refresh(intelligence)

    # =================================================
    # AUTOMATIC CALL CONTROL
    # =================================================

    terminal_decisions = {
        "callback_requested",
        "not_interested",
        "converted",
        "no_further_contact"
    }

    # =================================================
    # AUTOMATIC CALLBACK SCHEDULING
    # =================================================

    callback_scheduled = False
    callback_at = None

    if decision_type == "callback_requested":

        callback_text = "\n".join(
            message.get("text", "")
            for message in conversation
        )

        callback_at = extract_callback_time(
            callback_text
        )

        if callback_at:

            callback_result = schedule_callback(
                queue_id=queue_id,
                callback_at=callback_at,
                db=db
            )

            callback_scheduled = callback_result.get(
                "success",
                False
            )

    # =================================================
    # CALL END CONTROL
    # =================================================

    call_ended = False

    if (
        decision_type in terminal_decisions
        and decision_type != "callback_requested"
    ):

        now = datetime.utcnow()

        attempt.status = "completed"

        attempt.result = decision_type

        attempt.ended_at = now

        attempt.failure_reason = None

        queue_item.status = "completed"

        queue_item.completed_at = now

        queue_item.failure_reason = None

        # =================================================
        # UPDATE CRM
        # =================================================

        crm_result = update_lead_after_call(
            zoho_lead_id=lead.zoho_lead_id,
            outcome=decision_type,
            sentiment=(
                analysis.get("sentiment")
                or "neutral"
            ),
            summary=(
                analysis.get("summary")
                or ""
            )
        )

        db.commit()

        db.refresh(attempt)

        db.refresh(queue_item)

        call_ended = True

    else:

        crm_result = None

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",

        "message": (
            "AI response, call intelligence "
            "and decision saved successfully"
        ),

        "call": {
            "queue_id": queue_id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "phone": queue_item.phone,
            "lead_name": (
                f"{lead.first_name} "
                f"{lead.last_name}"
            ),
            "user_message": request.message,
            "ai_response": ai_response,
            "conversation": conversation,
            "call_ended": call_ended
        },

        "decision": {
            "decision": decision_type,
            "reason": decision.get(
                "reason",
                ""
            )
        },

        "intelligence": {
            "id": intelligence.id,
            "transcript": intelligence.transcript,
            "summary": intelligence.summary,
            "sentiment": intelligence.sentiment,
            "outcome": intelligence.outcome,
            "analyzed_at": intelligence.analyzed_at
        },

        "crm": crm_result
    }


# =====================================================
# END AI CALL + CRM UPDATE
# =====================================================

@app.post("/api/v1/telephony/ai-call/{queue_id}/end")
def end_ai_call(
    queue_id: int,
    db: Session = Depends(get_db)
):

    # =================================================
    # FIND QUEUE
    # =================================================

    queue_item = (
        db.query(CallQueue)
        .filter(
            CallQueue.id == queue_id
        )
        .first()
    )

    if not queue_item:

        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # =================================================
    # FIND LEAD
    # =================================================

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == queue_item.lead_id
        )
        .first()
    )

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    # =================================================
    # FIND LATEST ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(
            CallAttempt.attempt_number.desc()
        )
        .first()
    )

    if not attempt:

        raise HTTPException(
            status_code=400,
            detail="No call attempt found"
        )

    # =================================================
    # FIND LATEST INTELLIGENCE
    # =================================================

    intelligence = (
        db.query(CallIntelligence)
        .filter(
            CallIntelligence.queue_id == queue_id
        )
        .order_by(
            CallIntelligence.id.desc()
        )
        .first()
    )

    if not intelligence:

        raise HTTPException(
            status_code=400,
            detail="No call intelligence found"
        )

    # =================================================
    # FINAL CALL INTELLIGENCE ANALYSIS
    # =================================================

    try:

        analysis = analyze_call_transcript(
            intelligence.transcript
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Final call intelligence analysis failed: "
                f"{str(exc)}"
            )
        )

    intelligence.summary = (
        analysis.get("summary")
        or intelligence.summary
        or ""
    )

    intelligence.sentiment = (
        analysis.get("sentiment")
        or intelligence.sentiment
        or "neutral"
    )

    intelligence.outcome = (
        analysis.get("outcome")
        or intelligence.outcome
        or "answered"
    )

    # =================================================
    # COMPLETE CALL
    # =================================================

    now = datetime.utcnow()

    attempt.status = "completed"

    attempt.result = (
        intelligence.outcome
        or "answered"
    )

    attempt.ended_at = now

    attempt.failure_reason = None

    queue_item.status = "completed"

    queue_item.completed_at = now

    queue_item.failure_reason = None
    
    # =================================================
    # UPDATE CRM
    # =================================================

    crm_result = update_lead_after_call(
        zoho_lead_id=lead.zoho_lead_id,
        outcome=(
            intelligence.outcome
            or "answered"
        ),
        sentiment=(
            intelligence.sentiment
            or "neutral"
        ),
        summary=(
            intelligence.summary
            or ""
        )
    )

    # =================================================
    # SAVE DATABASE CHANGES
    # =================================================

    db.commit()

    db.refresh(attempt)

    db.refresh(queue_item)

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",
        "message": (
            "AI call ended and CRM updated "
            "successfully"
        ),

        "call": {
            "queue_id": queue_item.id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "call_result": attempt.result,
            "queue_status": queue_item.status,
            "ended_at": attempt.ended_at,
            "completed_at": queue_item.completed_at
        },

        "intelligence": {
            "summary": intelligence.summary,
            "sentiment": intelligence.sentiment,
            "outcome": intelligence.outcome
        },

        "crm": crm_result
    }


# =====================================================
# PROCESS DUE CALLBACKS
# =====================================================

@app.post("/api/v1/dialer/callback/process-due")
def process_due_callbacks_endpoint(
    db: Session = Depends(get_db)
):

    return process_due_callbacks(
        db
    )


# =====================================================
# SCHEDULE CALLBACK
# =====================================================

@app.post("/api/v1/dialer/callback/{queue_id}")
def schedule_callback_endpoint(
    queue_id: int,
    request: CallbackRequest,
    db: Session = Depends(get_db)
):

    result = schedule_callback(
        queue_id=queue_id,
        callback_at=request.callback_at,
        db=db
    )

    return result

