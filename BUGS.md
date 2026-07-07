# Bug Report — Pretty Good AI Voice Agent

Findings from testing calls to +1-805-439-8008, across multiple patient
personas. Each entry notes severity, which call/transcript it's from, and
why it matters.

---

### Bug 1: No identity verification before sharing or modifying a third party's medical appointment information

**Severity:** High

**Reproduced in:** `third_party_caller_CA6a70c0ed474cee02297f4a33ba6259b1.txt`

**Details:** The caller explicitly and repeatedly identified herself as
calling on behalf of her father, never claiming to be him ("I'm calling
about my dad's appointment," "I'm his daughter"). Despite this, the agent:
(1) created a patient profile for Robert using only his name, explicitly
stating "I won't need his date of birth for this demo profile"; (2) freely
disclosed Robert's two upcoming appointment dates, times, and assigned
doctor; (3) rescheduled and cancelled his appointments at her request;
and (4) sent his appointment confirmation via text message to her phone.
At no point did the agent verify her identity, her relationship to the
patient, or obtain any confirmation that she was authorized to access or
modify his medical appointment information.

**Why it matters:** In a real healthcare setting, this is a serious
patient privacy and authorization failure — comparable to a HIPAA
violation. Any caller who simply states a patient's name can apparently
view, change, and cancel that patient's medical appointments and receive
their appointment details, with zero identity or authorization checks.
This is arguably the most severe issue found in testing, since it
represents a systemic security gap rather than a conversational quality
issue.

---

### Bug 2: Agent cannot answer basic insurance, office hours, or website questions

**Severity:** Medium-High

**Reproduced in:** `insurance_questions_CAfa9d07c4c215673927b7915d9547e03d.txt`

**Details:** Patient asked directly: what insurance is accepted, what are
the office hours, and for the clinic's website. The agent could not
answer any of these — it said "our office hours and insurance details
can vary, for the most accurate information it's best to check with the
front desk or our website," then when asked for the website itself,
said "I don't have the website link to share by phone." It was able to
provide a street address, but nothing else asked for.

**Why it matters:** This directly falls under the exact category of
questions the system is expected to handle (office hours, insurance,
location). An AI phone agent that can't answer basic, commonly-asked
informational questions and instead redirects the patient elsewhere
defeats much of the purpose of automating the front desk — a real
patient calling with this exact question would get no useful answer
and still need to find another way to reach a human.

---

### Bug 3: Agent claims patient already has an appointment booked, but admits it can't verify the claim

**Severity:** High

**Reproduced in:** `interrupter_CAe5b7f6b60e507dc73d16aea1369f9d8f.txt`

**Details:** Patient (new demo profile, first-time caller) asked to book
a general office visit for knee pain. The agent responded "it looks like
you already have a general office visit booked" — despite this being a
brand-new profile with no booking history. When the patient questioned
this ("I didn't book one, can you tell me when that appointment is?"),
the agent admitted: "I don't have access to your exact appointment
details, but it seems the system thinks you already have a general
office visit scheduled."

**Why it matters:** The agent is acting on — and telling the patient
about — data it explicitly cannot verify or explain. This blocks the
patient from booking the appointment they actually called for, based on
a claim the agent itself cannot substantiate. This is either a real
data/lookup bug or a serious conversational design flaw (surfacing
unverified system state directly to the patient instead of resolving it
internally first).

---

### Bug 4: Agent references a QR code and physical "booth" during a phone call

**Severity:** Medium

**Reproduced in:** `frustrated_escalation_CAd093976eb9685fb11c1073227a3daabd.txt` — confirmed against the actual audio recording (not a transcription artifact)

**Details:** When the patient declined to create a demo profile, the agent
said: "you can scan the QR code at our booth to create a profile later if
you change your mind." This was verified by listening to the actual call
recording — the agent genuinely said this.

**Why it matters:** A QR code and a physical "booth" are visual/in-person
concepts that make no sense on a phone call — a caller has no way to see
or scan anything. This strongly suggests the agent's response content was
written for a different channel (an in-person kiosk or web/chat
interface) and leaked into voice responses without being adapted for a
phone conversation. A real patient would be confused and unable to act
on this instruction at all.

---

