/**
 * FraudGuard AI - Complete Lifecycle Flow & Interactive Decision Tree
 * Implements:
 * Transaction -> High Risk -> SMS Notification -> Call User (Attempt 1)
 * -> Attended (YES) / Not Attended (NO)
 * -> If NO -> Retry Call (Attempt 2)
 * -> If NO -> 🔒 AUTOMATED ACCOUNT HOLD -> 👨‍💼 ADMIN REVIEW
 * -> Admin Review Decision -> SAFE (UNHOLD ACCOUNT) or FRAUD (BLOCK ACCOUNT)
 */

document.addEventListener('DOMContentLoaded', () => {
    initSimulationHandler();
    initAlertActions();
    initCsvUpload();
    initCallWorkflowModal();
    initAdminReviewWorkflow();
});

// Toast notification helper
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-message toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: ${type === 'danger' ? '#DC2626' : (type === 'success' ? '#059669' : (type === 'warning' ? '#D97706' : '#1D4ED8'))};
        color: #FFFFFF;
        padding: 12px 20px;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
        animation: fadeIn 0.2s ease-out;
    `;
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// =========================================================================
// 1. SIMULATE TRANSACTION FLOW (Hackathon Core Demo Feature)
// =========================================================================

function initSimulationHandler() {
    const simBtn = document.getElementById('simulateTransactionBtn');
    const modal = document.getElementById('simulationModal');
    const closeBtn = document.getElementById('closeSimModal');
    const executeSimBtn = document.getElementById('executeSimBtn');
    const timeline = document.getElementById('simTimeline');
    const resultBox = document.getElementById('simResultBox');

    if (!simBtn || !modal) return;

    simBtn.addEventListener('click', () => {
        modal.classList.add('active');
        if (resultBox) resultBox.style.display = 'none';
        if (timeline) {
            timeline.innerHTML = `
                <div class="sim-step-item active" id="step-1">
                    <span class="sim-step-badge">STEP 01</span>
                    <div>
                        <div class="sim-step-title" style="font-weight: 700; color: #FFF; font-size: 14px;">Awaiting Simulation Trigger</div>
                        <div style="font-size: 12px; color: #94A3B8;">Click "Run Live Simulation" to inject a transaction payload into the defense pipeline.</div>
                    </div>
                </div>
            `;
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });
    }

    if (executeSimBtn) {
        executeSimBtn.addEventListener('click', async () => {
            executeSimBtn.disabled = true;
            executeSimBtn.innerHTML = `<span>Evaluating Defense Pipeline...</span>`;

            try {
                const res = await fetch('/api/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();

                if (!data.success) {
                    showToast('Simulation failed: ' + (data.message || 'Unknown error'), 'danger');
                    executeSimBtn.disabled = false;
                    executeSimBtn.innerText = 'Run Live Simulation';
                    return;
                }

                if (timeline && data.steps) {
                    timeline.innerHTML = '';
                    for (let i = 0; i < data.steps.length; i++) {
                        const step = data.steps[i];
                        const stepEl = document.createElement('div');
                        stepEl.className = 'sim-step-item';
                        stepEl.id = `step-node-${i + 1}`;
                        stepEl.innerHTML = `
                            <span class="sim-step-badge">STEP 0${step.step}</span>
                            <div>
                                <div style="font-weight: 700; color: #FFF; font-size: 13px;">${step.title}</div>
                                <div style="font-size: 12px; color: #CBD5E1; margin-top: 2px;">${step.detail}</div>
                            </div>
                        `;
                        timeline.appendChild(stepEl);
                        await new Promise(r => setTimeout(r, 400));
                        stepEl.classList.add('active', 'completed');
                    }
                }

                if (resultBox) {
                    resultBox.style.display = 'block';
                    const tx = data.transaction;

                    document.getElementById('resTxId').innerText = tx.transaction_id;
                    document.getElementById('resAmount').innerText = `₹${tx.amount.toLocaleString()}`;
                    document.getElementById('resScore').innerText = `${tx.risk_score} / 100`;
                    document.getElementById('resLevel').innerText = tx.risk_level;
                    document.getElementById('resLevel').className = `risk-tag ${tx.risk_level.toLowerCase()}`;
                    
                    const flowLaunchBtn = document.getElementById('resLaunchCallWorkflowBtn');
                    if (flowLaunchBtn) {
                        flowLaunchBtn.dataset.accountId = data.account_id;
                        flowLaunchBtn.dataset.txId = tx.transaction_id;
                        flowLaunchBtn.dataset.amount = tx.amount;
                        flowLaunchBtn.dataset.location = tx.location;
                    }
                }

                updateDashboardDOM(data.updated_metrics, data.transaction);
                showToast(`HIGH RISK Detected on ${data.account_id}! User Notification SMS Sent.`, 'warning');

            } catch (err) {
                console.error(err);
                showToast('Network error during simulation.', 'danger');
            } finally {
                executeSimBtn.disabled = false;
                executeSimBtn.innerText = 'Run Another Simulation';
            }
        });
    }
}

function updateDashboardDOM(metrics, newTx) {
    if (!metrics) return;

    const txTotalEl = document.getElementById('metric-total-tx');
    const suspTotalEl = document.getElementById('metric-susp-tx');
    const critTotalEl = document.getElementById('metric-crit-tx');
    const valTotalEl = document.getElementById('metric-total-val');
    const rateTotalEl = document.getElementById('metric-fraud-rate');
    const heldCountEl = document.getElementById('metric-held-count');
    const blockedCountEl = document.getElementById('metric-blocked-count');

    if (txTotalEl) txTotalEl.innerText = metrics.total_transactions.toLocaleString();
    if (suspTotalEl) suspTotalEl.innerText = metrics.suspicious_transactions.toLocaleString();
    if (critTotalEl) critTotalEl.innerText = metrics.critical_transactions.toLocaleString();
    if (valTotalEl) valTotalEl.innerText = metrics.formatted_value;
    if (rateTotalEl) rateTotalEl.innerText = `${metrics.fraud_detection_rate}%`;
    if (heldCountEl) heldCountEl.innerText = metrics.held_accounts || '0';
    if (blockedCountEl) blockedCountEl.innerText = metrics.blocked_accounts || '0';

    const recentTableBody = document.querySelector('#recentThreatsTable tbody');
    if (recentTableBody && newTx) {
        const tr = document.createElement('tr');
        tr.className = `risk-${newTx.risk_level.toLowerCase()}`;
        tr.style.backgroundColor = 'rgba(16, 185, 129, 0.12)';
        tr.innerHTML = `
            <td style="font-weight: 700; font-family: 'JetBrains Mono', monospace; color: #34D399;">${newTx.transaction_id}</td>
            <td>
                <a href="/accounts/${newTx.account_id}" style="color: #CBD5E1; text-decoration: underline;">
                    ${newTx.account_id}
                </a>
            </td>
            <td style="font-weight: 700; font-family: 'JetBrains Mono', monospace;">₹${newTx.amount.toLocaleString()}</td>
            <td>${newTx.location}</td>
            <td>${newTx.time_str}</td>
            <td><span class="mono" style="font-weight: 700; color: ${newTx.risk_score >= 81 ? '#F87171' : '#34D399'}">${newTx.risk_score}</span></td>
            <td><span class="risk-tag ${newTx.risk_level.toLowerCase()}">${newTx.risk_level}</span></td>
            <td>
                <button class="btn btn-green btn-sm btn-start-call-flow" data-account-id="${newTx.account_id}" data-tx-id="${newTx.transaction_id}" data-amount="${newTx.amount}" data-location="${newTx.location}">
                    <i class="icon-phone"></i> Verify Call
                </button>
            </td>
            <td>
                <a href="/transactions/${newTx.transaction_id}" class="btn btn-secondary btn-sm">View</a>
            </td>
        `;
        recentTableBody.insertBefore(tr, recentTableBody.firstChild);
    }
}

// =========================================================================
// 2. MULTI-STAGE USER CALL & DECISION TREE WORKFLOW MODAL
// =========================================================================

let currentFlowAccId = null;
let currentFlowTxId = null;
let currentFlowAmount = null;
let currentFlowLocation = null;
let currentFlowAttempt = 1;

function initCallWorkflowModal() {
    const modal = document.getElementById('callWorkflowModal');
    const closeBtn = document.getElementById('closeCallWorkflowModal');

    // Launch flow buttons
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-start-call-flow') || (e.target.id === 'resLaunchCallWorkflowBtn' ? e.target : null);
        if (btn) {
            currentFlowAccId = btn.dataset.accountId || 'ACC102';
            currentFlowTxId = btn.dataset.txId || 'TX10045';
            currentFlowAmount = btn.dataset.amount || '75,000';
            currentFlowLocation = btn.dataset.location || 'Dubai';
            currentFlowAttempt = 1;

            if (modal) {
                modal.classList.add('active');
                startCallAttempt(1);
            }
        }
    });

    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });
    }

    // Step 1: User answered Call Attempt
    const callAttendedBtn = document.getElementById('flowCallAttendedBtn');
    const callNotAttendedBtn = document.getElementById('flowCallNotAttendedBtn');

    if (callAttendedBtn) {
        callAttendedBtn.addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/accounts/${currentFlowAccId}/call-step`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        attempt: currentFlowAttempt,
                        outcome: 'ATTENDED',
                        transaction_id: currentFlowTxId,
                        amount: currentFlowAmount,
                        location: currentFlowLocation
                    })
                });
                const data = await res.json();
                renderVerificationStage(data.script);
            } catch (err) {
                showToast('Error processing call step', 'danger');
            }
        });
    }

    if (callNotAttendedBtn) {
        callNotAttendedBtn.addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/accounts/${currentFlowAccId}/call-step`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        attempt: currentFlowAttempt,
                        outcome: 'NOT_ATTENDED',
                        transaction_id: currentFlowTxId,
                        amount: currentFlowAmount,
                        location: currentFlowLocation
                    })
                });
                const data = await res.json();

                if (data.next_step === 'RETRY_CALL') {
                    currentFlowAttempt = 2;
                    showToast('Call #1 was unattended. Retrying call (Attempt #2)...', 'warning');
                    startCallAttempt(2);
                } else if (data.next_step === 'SMS_DECISION') {
                    showToast('Call #2 missed. Dispatched urgent SMS verification query to cardholder.', 'warning');
                    renderSmsDecisionStage(data);
                } else if (data.next_step === 'ACCOUNT_HOLD') {
                    showToast(data.message, 'danger');
                    renderAccountHoldStage(data);
                }
            } catch (err) {
                showToast('Error handling unattended call', 'danger');
            }
        });
    }

    // Verification choices when call is attended
    const verifySafeBtn = document.getElementById('flowVerifySafeBtn');
    const verifyFraudBtn = document.getElementById('flowVerifyFraudBtn');

    if (verifySafeBtn) {
        verifySafeBtn.addEventListener('click', async () => {
            await resolveAdminReview('SAFE', 'Verified by cardholder during voice authentication.');
            if (modal) modal.classList.remove('active');
        });
    }

    if (verifyFraudBtn) {
        verifyFraudBtn.addEventListener('click', async () => {
            await resolveAdminReview('FRAUD', 'Customer confirmed unauthorized fraud on phone call.');
            if (modal) modal.classList.remove('active');
        });
    }

    // SMS Decision choices (when 2 calls are missed)
    const smsSelfSafeBtn = document.getElementById('flowSmsSelfSafeBtn');
    const smsOthersFraudBtn = document.getElementById('flowSmsOthersFraudBtn');
    const smsNoResponseBtn = document.getElementById('flowSmsNoResponseBtn');

    if (smsSelfSafeBtn) {
        smsSelfSafeBtn.addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/accounts/${currentFlowAccId}/sms-response`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        decision: 'SELF',
                        transaction_id: currentFlowTxId
                    })
                });
                const data = await res.json();
                showToast(`✅ ${data.message}`, 'success');
                
                const badge = document.getElementById(`account-status-badge-${currentFlowAccId}`) || document.getElementById('accountStatusBadge');
                if (badge) {
                    badge.innerText = 'ACTIVE';
                    badge.className = 'risk-tag low';
                }
                if (modal) modal.classList.remove('active');
            } catch (err) {
                showToast('Error recording SMS verification', 'danger');
            }
        });
    }

    if (smsOthersFraudBtn) {
        smsOthersFraudBtn.addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/accounts/${currentFlowAccId}/sms-response`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        decision: 'OTHERS',
                        transaction_id: currentFlowTxId
                    })
                });
                const data = await res.json();
                showToast(`🚨 ${data.message}`, 'danger');
                
                const badge = document.getElementById(`account-status-badge-${currentFlowAccId}`) || document.getElementById('accountStatusBadge');
                if (badge) {
                    badge.innerText = 'BLOCKED';
                    badge.className = 'risk-tag critical';
                }
                if (modal) modal.classList.remove('active');
            } catch (err) {
                showToast('Error recording SMS fraud report', 'danger');
            }
        });
    }

    if (smsNoResponseBtn) {
        smsNoResponseBtn.addEventListener('click', () => {
            renderAccountHoldStage({
                message: `SMS was unanswered by cardholder after timeout. Account ${currentFlowAccId} is placed on AUTOMATIC ACCOUNT HOLD and queued for Admin Review.`
            });
        });
    }
}

// Real Audio Telephony Simulation via Web Audio API & SpeechSynthesis
function playPhoneRingSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc1 = audioCtx.createOscillator();
        const osc2 = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc1.type = 'sine';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(440, audioCtx.currentTime);
        osc2.frequency.setValueAtTime(480, audioCtx.currentTime);

        gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
        gain.gain.setValueAtTime(0, audioCtx.currentTime + 1.2);

        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(audioCtx.destination);

        osc1.start();
        osc2.start();
        osc1.stop(audioCtx.currentTime + 1.2);
        osc2.stop(audioCtx.currentTime + 1.2);
    } catch (e) {
        console.warn('Audio ringtone notice:', e);
    }
}

function speakVoiceScript(text) {
    if ('speechSynthesis' in window) {
        try {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.lang = 'en-IN';
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn('Speech synthesis notice:', e);
        }
    }
}

async function startCallAttempt(attemptNum) {
    document.getElementById('flowStepKicker').innerText = `WORKFLOW STEP 04: CELLULAR CALL (ATTEMPT ${attemptNum}/2)`;
    document.getElementById('flowCallingPane').style.display = 'block';
    document.getElementById('flowVerifyPane').style.display = 'none';
    if (document.getElementById('flowSmsDecisionPane')) document.getElementById('flowSmsDecisionPane').style.display = 'none';
    document.getElementById('flowHoldReviewPane').style.display = 'none';

    document.getElementById('flowCallAttemptTitle').innerText = attemptNum === 1 ? '📞 Outbound Cellular Call Attempt #1' : '📞 Retry Outbound Call Attempt #2';
    
    const metaEl = document.getElementById('flowCallMeta');
    if (metaEl) {
        metaEl.innerHTML = `
            Placing live cellular call to physical phone for <strong>${currentFlowAccId}</strong> regarding ₹${currentFlowAmount} in ${currentFlowLocation}...<br>
            <div style="margin: 10px 0; font-size: 13px; color: #38BDF8; font-weight: 700; font-family: 'JetBrains Mono', monospace;">
                Target: +91 8148534339
            </div>
            <div style="display: flex; gap: 8px; justify-content: center; margin-top: 10px;">
                <a href="tel:+918148534339" class="btn btn-outline btn-sm" style="color: #38BDF8; border-color: #38BDF8; font-size: 12px; padding: 4px 12px;">
                    <i class="icon-phone-forwarded"></i> 📱 Open Windows Phone Link / System Dialer (+91 8148534339)
                </a>
            </div>
        `;
    }

    // Trigger backend cellular call via Twilio
    try {
        const res = await fetch(`/api/accounts/${currentFlowAccId}/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transaction_id: currentFlowTxId,
                amount: currentFlowAmount,
                location: currentFlowLocation
            })
        });
        const data = await res.json();
        if (data.telephony && data.telephony.mode === 'LIVE_TWILIO') {
            showToast(`📞 Live cellular call dispatched to physical phone ${data.phone}!`, 'success');
        } else if (data.telephony && data.telephony.mode === 'CREDENTIALS_REQUIRED') {
            showToast(data.telephony.message, 'warning');
        }
    } catch (err) {
        console.error(err);
    }
}

function renderVerificationStage(script) {
    const speechText = script || `Hello, this is FraudGuard AI security desk. We detected an unusual transaction of ₹${currentFlowAmount} from ${currentFlowLocation}. Did you authorize this?`;

    document.getElementById('flowStepKicker').innerText = `WORKFLOW STEP 05: CALL ATTENDED → CARDHOLDER VERIFICATION`;
    document.getElementById('flowCallingPane').style.display = 'none';
    document.getElementById('flowVerifyPane').style.display = 'block';
    if (document.getElementById('flowSmsDecisionPane')) document.getElementById('flowSmsDecisionPane').style.display = 'none';
    document.getElementById('flowHoldReviewPane').style.display = 'none';

    document.getElementById('flowTranscriptText').innerText = speechText;
}

function renderSmsDecisionStage(data) {
    document.getElementById('flowStepKicker').innerText = `WORKFLOW STEP 06: CALLS MISSED (2/2) → 📱 SMS VERIFICATION DECISION`;
    document.getElementById('flowCallingPane').style.display = 'none';
    document.getElementById('flowVerifyPane').style.display = 'none';
    const smsMsg = data.sms_text || `Bank Alert: A transaction of ₹${currentFlowAmount} at ${currentFlowLocation} was requested on Account ${currentFlowAccId}. Was this transaction done by you or others?`;
    if (document.getElementById('flowSmsDecisionPane')) {
        document.getElementById('flowSmsDecisionPane').style.display = 'block';
        if (document.getElementById('flowSmsRecipientPhone')) {
            document.getElementById('flowSmsRecipientPhone').innerText = data.phone || '+91 8148534339';
        }
        if (document.getElementById('flowSmsContentText')) {
            document.getElementById('flowSmsContentText').innerText = smsMsg;
        }
    }
    document.getElementById('flowHoldReviewPane').style.display = 'none';
    showToast(`📱 Real SMS sent to physical phone ${data.phone || '+91 8148534339'}. Check mobile handset!`, 'info');
}

function renderAccountHoldStage(data) {
    document.getElementById('flowStepKicker').innerText = `WORKFLOW STEP 07: UNANSWERED → 🔒 ACCOUNT HOLD & ADMIN REVIEW`;
    document.getElementById('flowCallingPane').style.display = 'none';
    document.getElementById('flowVerifyPane').style.display = 'none';
    if (document.getElementById('flowSmsDecisionPane')) document.getElementById('flowSmsDecisionPane').style.display = 'none';
    document.getElementById('flowHoldReviewPane').style.display = 'block';

    document.getElementById('flowHoldAccId').innerText = currentFlowAccId;
    document.getElementById('flowHoldReason').innerText = data.message;
}

// =========================================================================
// 3. ADMIN REVIEW WORKFLOW (SAFE -> UNHOLD | FRAUD -> BLOCK)
// =========================================================================

function initAdminReviewWorkflow() {
    // Review queue buttons on dashboard or account details
    document.querySelectorAll('.btn-admin-review-safe').forEach(btn => {
        btn.addEventListener('click', async () => {
            const accId = btn.dataset.accountId;
            await resolveAdminReview('SAFE', 'Cleared by Security Investigator', accId);
        });
    });

    document.querySelectorAll('.btn-admin-review-fraud').forEach(btn => {
        btn.addEventListener('click', async () => {
            const accId = btn.dataset.accountId;
            await resolveAdminReview('FRAUD', 'Confirmed fraud by Security Investigator', accId);
        });
    });

    const flowAdminSafeBtn = document.getElementById('flowAdminSafeBtn');
    const flowAdminFraudBtn = document.getElementById('flowAdminFraudBtn');

    if (flowAdminSafeBtn) {
        flowAdminSafeBtn.addEventListener('click', async () => {
            await resolveAdminReview('SAFE', 'Cleared by Admin Review queue', currentFlowAccId);
            const modal = document.getElementById('callWorkflowModal');
            if (modal) modal.classList.remove('active');
        });
    }

    if (flowAdminFraudBtn) {
        flowAdminFraudBtn.addEventListener('click', async () => {
            await resolveAdminReview('FRAUD', 'Confirmed Fraud in Admin Review queue', currentFlowAccId);
            const modal = document.getElementById('callWorkflowModal');
            if (modal) modal.classList.remove('active');
        });
    }
}

async function resolveAdminReview(decision, notes, accountId) {
    const acc = accountId || currentFlowAccId;
    try {
        const res = await fetch(`/api/accounts/${acc}/admin-review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                decision: decision,
                transaction_id: currentFlowTxId || '',
                notes: notes
            })
        });
        const data = await res.json();

        if (decision === 'SAFE') {
            showToast(`✅ ${data.message}`, 'success');
        } else {
            showToast(`🚨 ${data.message}`, 'danger');
        }

        // Live DOM Badge update
        const badge = document.getElementById(`account-status-badge-${acc}`) || document.getElementById('accountStatusBadge');
        if (badge) {
            badge.innerText = data.status;
            badge.className = `risk-tag ${data.status.toLowerCase()}`;
        }

        // Refresh review queue row if present
        const reviewRow = document.getElementById(`review-row-${acc}`);
        if (reviewRow) {
            reviewRow.remove();
        }

    } catch (err) {
        showToast('Error recording admin review decision', 'danger');
    }
}

// =========================================================================
// 4. ALERT REVIEW & DISMISS WORKFLOW
// =========================================================================

function initAlertActions() {
    document.querySelectorAll('.btn-review-alert').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const alertId = e.target.dataset.alertId;
            try {
                const res = await fetch(`/api/alerts/${alertId}/review`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, 'success');
                    const badge = document.getElementById(`status-badge-${alertId}`);
                    if (badge) {
                        badge.innerText = 'UNDER_INVESTIGATION';
                        badge.className = 'risk-tag medium';
                    }
                }
            } catch (err) {
                showToast('Error updating alert status', 'danger');
            }
        });
    });

    document.querySelectorAll('.btn-dismiss-alert').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const alertId = e.target.dataset.alertId;
            try {
                const res = await fetch(`/api/alerts/${alertId}/dismiss`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, 'info');
                    const row = document.getElementById(`alert-row-${alertId}`);
                    if (row) row.style.opacity = '0.3';
                }
            } catch (err) {
                showToast('Error dismissing alert', 'danger');
            }
        });
    });
}

// =========================================================================
// 5. CSV UPLOAD HANDLER
// =========================================================================

function initCsvUpload() {
    const uploadForm = document.getElementById('csvUploadForm');
    const fileInput = document.getElementById('csvFileInput');
    const resultsContainer = document.getElementById('uploadResultsContainer');
    const resultsTableBody = document.querySelector('#uploadResultsTable tbody');
    const countBadge = document.getElementById('uploadCountBadge');

    if (!uploadForm || !fileInput) return;

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) {
            showToast('Please select a CSV file first.', 'danger');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerText = 'Processing Batch Analysis...';

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.success) {
                showToast(data.message, 'success');
                if (resultsContainer) resultsContainer.style.display = 'block';
                if (countBadge) countBadge.innerText = `${data.count} Records Processed`;

                if (resultsTableBody && data.results) {
                    resultsTableBody.innerHTML = data.results.map(r => `
                        <tr class="risk-${r.risk_level.toLowerCase()}">
                            <td class="mono" style="font-weight: 700; color: #34D399;">${r.transaction_id}</td>
                            <td>${r.account_id}</td>
                            <td class="mono" style="font-weight: 700;">₹${r.amount.toLocaleString()}</td>
                            <td>${r.location}</td>
                            <td>${r.time}</td>
                            <td class="mono" style="font-weight: 700;">${r.risk_score}</td>
                            <td><span class="risk-tag ${r.risk_level.toLowerCase()}">${r.risk_level}</span></td>
                            <td><a href="/transactions/${r.transaction_id}" class="btn btn-secondary btn-sm">Inspect</a></td>
                        </tr>
                    `).join('');
                }
            } else {
                showToast(data.message || 'Error processing CSV', 'danger');
            }
        } catch (err) {
            console.error(err);
            showToast('Network error while uploading file.', 'danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = 'Upload & Analyze CSV';
        }
    });
}
