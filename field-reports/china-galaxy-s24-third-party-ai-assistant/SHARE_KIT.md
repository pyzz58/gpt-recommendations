# Publication and outreach kit (English)

**Purpose:** Help others reproduce and critique an anonymized, paused Samsung Galaxy S24 assistant experiment. These are **drafts, not proof of an external posting**. Please follow the current rules of each destination before submitting. Avoid posting substantially identical messages to multiple communities.

**Existing public report:** [Galaxy S24 China-market assistant field report](README.md)  
**Proposed standalone repository:** \`galaxy-s24-china-ai-assistant-experiment\`  
**Repository description:** "Real-device Galaxy S24 CHC / One UI 8.5 experiment: side-key 101 vs 5, failed voice session, working ACTION_ASSIST, and STT limitations."  
**Suggested GitHub Topics:** \`samsung\`, \`galaxy-s24\`, \`one-ui\`, \`android-16\`, \`android-assistant\`, \`bixby\`, \`action-assist\`, \`adb\`.

## 1. SideKey GitHub issue — actual device findings

**Suggested title:** Device report: SM-S9210 (CHC, One UI 8.5) confirms assistant side-key routing via 5; ACTION_ASSIST works

**Suggested text:**

> I tested the standard assistant route on a China-market Samsung Galaxy S24 (SM-S9210, CHC, Android 16 / One UI 8.5) and wanted to contribute a second device observation to the work documented by SideKey.
>
> Observed original settings: \`function_key_config_longpress_selected_item=long_press_wake_bixby\` and \`power_button_long_press=101\`. Selecting a third-party default assistant alone did not redirect the physical long press; Bixby still opened.
>
> After temporarily setting \`power_button_long_press=5\` through ADB, SystemUI began invoking the selected third-party assistant. My conventional VoiceInteractionService could be invoked but its SessionService failed to bind with \`not found\` (exact cause unresolved). A separate Activity-only assistant using \`android.intent.action.ASSIST\` **did** work on the same device; SystemUI opened its AssistActivity and MainActivity. The same launch path later worked in the main app. The original setting (101) was restored after testing.
>
> This observation applies only to SM-S9210 / CHC / One UI 8.5. Reboot persistence was not tested. The app's cloud speech recognition did not complete, so this is a system-launch observation, **not** a finished Bixby replacement.
>
> Anonymized engineering notes: https://github.com/pyzz58/gpt-recommendations/blob/main/field-reports/china-galaxy-s24-third-party-ai-assistant/README.md
>
> Thank you for publishing the original Samsung-specific side-key findings; they helped identify the correct layer to test.

**Posting status:** Not posted. Connected GitHub integration returned HTTP 403 when attempting to create an Issue in the SideKey repository. The repository explicitly invites device reports; this message can be submitted by an account with normal issue-posting access.

## 2. Android developer community post

**Suggested title:** On a China-market S24, ACTION_ASSIST worked where VoiceInteractionSessionService didn't

**Suggested text:**

> I tried to make the physical side-key long press start a custom Android digital assistant on a Chinese-market Galaxy S24 (SM-S9210, Android 16 / One UI 8.5).
>
> I hit two distinct blockers. First, simply selecting my app as the default assistant did not override Samsung's \`power_button_long_press=101\` Bixby route. Temporarily using the framework assistant value \`5\` made SystemUI call the selected assistant. Second, my VoiceInteractionService was invoked, but Android failed to bind VoiceInteractionSessionService with \`not found\` even though the component existed in the installed APK. A different third-party assistant could bind its session, so I couldn't honestly call it a universal firmware ban.
>
> The surprising part: I removed the voice-service registration and instead exposed a standard \`ACTION_ASSIST\` Activity. The same phone then successfully launched my app through SystemUI from the physical side key, including in the main app package.
>
> The full Chinese voice pipeline still **did not** work: there was no usable standard RecognitionService, and cloud STT attempts eventually returned HTTP 401. The project is paused, but the side-key/Activity-only result may help others debugging Samsung assistant integration.
>
> I've documented the test sequence, sanitized logs, negative controls, and rollback caveats here: https://github.com/pyzz58/gpt-recommendations/blob/main/field-reports/china-galaxy-s24-third-party-ai-assistant/README.md
>
> Has anyone seen an equivalent ACTION_ASSIST result on a different CSC or One UI release?

**Posting status:** Not posted. Check live subreddit rules and submit as a substantive technical discussion, not a bare self-promotional link. Avoid posting where self-promotion is prohibited.

## 3. DEV Community / Hashnode article outline

**Proposed title:** How I Got a Custom AI Assistant to Launch from the Side Key on a China-Market Galaxy S24

**Subheading:** The Android-supported ACTION_ASSIST route worked; the Chinese voice pipeline did not.

**Suggested sections:**

1. The goal: system assistant, not a home-screen chat shortcut
2. Why changing the default assistant was insufficient on this firmware
3. The SideKey clue: original behavior 101 versus the framework assistant action 5
4. The failed VoiceInteractionSessionService experiments and why their root cause remains unknown
5. The positive control: another assistant's session binds successfully
6. The alternative: ACTION_ASSIST Activity-only and the SystemUI launch trace
7. Chinese STT reality: no native provider, main-thread bug, then cloud HTTP 401
8. What genuinely worked, what never worked, and lessons for Android developers

End with a link to the original full field report and a request for device-specific confirmations. Do not claim successful STT or a fully functioning Bixby replacement.

**Posting status:** Not posted. No connected publisher account/write permission is available in this chat.

## 4. Standalone GitHub repository creation

The existing report is public and linked from the source repository homepage. The connected GitHub actions currently do not provide **create repository** or **edit repository topics** operations.

An explicit, reviewable [publication script](publish_standalone_repo.sh) was added to the public folder. It checks that the GitHub CLI is authenticated to the expected account, creates a new public repository, copies the original English report as the new root README, adds an issue template that prohibits sensitive device information, and adds the suggested Topics.

**This script has not been executed by ChatGPT.** It must be run through the GitHub-authenticated development machine or another authorized GitHub environment. Review it before execution.

## 5. Privacy checklist

- No real name, postal address, workplace, phone number, serial, IMEI, Android ID, recording, or API Key.
- No local home-directory paths or unredacted logcat exports.
- Keep the device model/CSC and technical component names; these are necessary to interpret reproducibility.
- The public GitHub username and contribution history remain visible to readers.
- Submit only once to a relevant community; do not automate repetitive cross-posting.
