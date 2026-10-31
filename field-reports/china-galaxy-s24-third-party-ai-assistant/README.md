# Trying to Replace the AI Assistant on a China-Market Samsung Galaxy S24

**An independent Android engineering field report — what was attempted, what worked, what failed, and why the experiment stopped**

**Status:** Paused / experimental, **not a finished voice assistant**  
**Device tested:** Galaxy S24 SM-S9210, China-market (CHC), Android 16 / One UI 8.5  
**Period:** Late October–November 2026  
**Publication:** Technical lessons only; no APK, full source repository, private logs, or credentials are distributed.

> **Summary.** A custom Android app was successfully invoked by a *physical long-press* of the Galaxy S24 side key using Android's official assistant mechanism. A first implementation built around VoiceInteractionService repeatedly failed to bind its VoiceInteractionSessionService. Switching to an Activity handling ACTION_ASSIST fixed the launch path, both in an isolated test package and in the main app. However, an end-to-end Chinese voice assistant was **not** completed: the device exposed no usable standard third-party speech recognizer, and later cloud speech-to-text (STT) requests returned HTTP 401. After documenting the results, the project was voluntarily paused.

## The experiment at a glance

**Tested on a China-market Galaxy S24 (SM-S9210, CHC, Android 16 / One UI 8.5).**

| Attempt | Outcome |
| --- | --- |
| Default assistant + Samsung's original long-press behavior (101) | **Bixby still opened** |
| Android assistant behavior (5) + VoiceInteractionService | **Assistant invoked, but SessionService failed to bind** |
| Android assistant behavior (5) + ACTION_ASSIST Activity | **Worked: physical side key launched the custom app** |
| Chinese cloud STT → spoken command | **Not completed: repeated HTTP 401** |

~~~mermaid
flowchart TD
    A["Physical side-key long press"] --> B{"System long-press behavior"}
    B -->|101 in tested firmware| C["Samsung / Bixby path"]
    B -->|5 in tested firmware| D["SystemUI AssistManager"]
    D --> E{"Selected assistant architecture"}
    E -->|VoiceInteractionService| F["SessionService bind: not found"]
    E -->|ACTION_ASSIST Activity| G["AssistActivity → MainActivity"]
    G --> H["Cloud STT: HTTP 401; voice loop incomplete"]
    style F fill:#fce8e6,stroke:#a92d2d,color:#202124
    style G fill:#e6f4ea,stroke:#237a3b,color:#202124
~~~

**The useful result is the supported Android side-key launch path—not a claim of a finished Bixby replacement.** The full experimental timeline, troubleshooting evidence, rollback instructions, and limitations are below.

## 1. Motivation: a real assistant, not another shortcut

The idea was to make the Chinese-market Galaxy S24's hardware side key launch a user-selected assistant capable of conversational Chinese interaction, rather than simply opening a chat app from a home-screen icon or double-press shortcut.

The desired experience was:

1. Long-press the side key to open the independently developed assistant.
2. Automatically begin a single, explicitly user-triggered voice interaction.
3. Turn spoken Chinese into text.
4. Handle simple instructions locally (for example, opening Calculator or handing an alarm to Samsung Clock).
5. Route general questions to a user-configured large language model, optionally returning verifiable search sources.
6. Read the answer aloud and support follow-up questions.

The boundaries were deliberate: **no root, firmware flashing, Bixby package removal, private Samsung service bypass, accessibility-based key interception, or permanent dependence on a desktop computer**. A workflow suitable for normal internet access in mainland China was a goal, not a verified final result.

This was an exploratory integration experiment, not a Samsung modification, commercial product, or claim of feature parity with Bixby.

## 2. The hardware and software boundary

| Component | Tested configuration |
| --- | --- |
| Phone | Samsung Galaxy S24, SM-S9210 |
| Firmware region | CHC (China-market) |
| Android | 16 / API 36 |
| One UI | 8.5 |
| Main experimental application | com.app.assistant |
| Android interfaces | ASSISTANT role, VoiceInteractionService, later ACTION_ASSIST |
| Local commands | Chinese text parser and Android intents |
| Initial speech route | Android SpeechRecognizer |
| Later speech route | Configurable cloud STT |
| Development method | Kotlin/Gradle builds, ADB inspection, unit tests, controlled phone tests |

The observations apply to **one tested device**, not necessarily to other CSCs, firmware versions, Samsung models, or Android vendors.

Initial project research considered existing public Android-assistant implementations, including [Gimi](https://github.com/pony-huang/Gimi) and [ai-assistant-android](https://github.com/souravanand001/ai-assistant-android). The work described here concerns the experimental app and its integration behavior; this report does not redistribute those projects' code.

## 3. Chronology and evidence

| Stage | Experiment | Result |
| --- | --- | --- |
| Early MVP | Register assistant components and use native Android Chinese speech recognition | Installed, but speech recognition returned “no selected voice recognition service.” |
| 3.1 | Test typed Chinese command routing | **“打开计算器” (“Open Calculator”) launched Samsung Calculator through the app itself.** |
| First system-assistant test | Select com.app.assistant as Android's default assistant | Role changed, but physical long-press still opened Bixby. |
| Side-key investigation | Compare Samsung setting UI with underlying power-button behavior | Found a Samsung-specific long-press value of 101 on this device. |
| Side-key ADB experiment | Temporarily change the underlying long-press behavior to 5 | SystemUI invoked the selected third-party assistant instead of Bixby. |
| 3.2 | Diagnose VoiceInteractionSessionService; examine manifest, component, lifecycle, process | System-side session binding failed with “not found” before service creation. |
| 3.2.1 | Build non-debuggable variant to test the debug-flag hypothesis | **Same failure.** Disabling debuggability was not a sufficient remedy. |
| Platform control | Use the installed ChatGPT Android app as the default assistant with the same long-press routing | Its session service bound successfully and assistant Activity opened. |
| Separate Activity-only package | Register ACTION_ASSIST Activity, with no VoiceInteractionService | **Physical side-key launch succeeded.** |
| 3.3 main app | Adopt Activity-only architecture in the original app ID | **Physical side-key launch succeeded again**, opening MainActivity without a crash. |
| 3.4 | Attempt cloud STT with a real recording | Found a main-thread network call defect, fixed by moving blocking work to IO; next attempt ended with IOException. |
| 3.4.1 | Add minimal HTTP-status diagnostics; retry STT authentication | Multiple requests returned **HTTP 401**. No transcript obtained; experiment stopped. |

The table separates outcomes observed on the physical phone from functionality that merely compiled or passed local tests.

## 4. Native recognition did not exist for this third-party use case

The initial recognition failure was:

~~~text
no selected voice recognition service
~~~

Read-only inspection found no selected standard Android voice_recognition_service and no external public RecognitionService the app could use. A placeholder service in an early build did not provide recognition and was removed.

Samsung-specific on-device speech capabilities existed, but there was no evidence that a normal third-party APK could bind those private components through the standard Android SpeechRecognizer API. No attempt was made to bypass signature or proprietary binding restrictions.

**Takeaway:** RECORD_AUDIO permission and a working microphone do not guarantee that Android offers a compatible speech-recognition engine. Audio capture and speech transcription require separate validation.

## 5. The side key exposed two different routing layers

Even with the custom application selected as the Android ASSISTANT role holder, the physical button initially produced:

~~~text
BixbyService: startBixbyService ... longPress=true
PhoneWindowManagerExt: run wake Bixby
PhoneWindowManagerExt: consume powerLongPress
~~~

Investigation was informed by the independently maintained [SideKey project](https://github.com/quinnjr/sidekey), which describes a difference between Samsung's visible Side button choice and the lower-level framework value on certain One UI 8+ builds.

On this device, the observed values were:

~~~text
function_key_config_longpress_selected_item = long_press_wake_bixby
power_button_long_press = 101
~~~

Android's open-source framework defines **5** as the long-press assistant action. A temporary ADB experiment changed only the underlying behavior value to 5 after recording the original:

~~~sh
adb shell settings get global power_button_long_press
adb shell settings put global power_button_long_press 5
~~~

With the test app selected as the default digital assistant, the phone then logged:

~~~text
EID_INVOKE_DIGITAL_ASSISTANT
DigitalAssistantApp=com.app.assistant
InvocationType=Side button
AssistManager: startAssistInternal
~~~

The important finding was that **setting the default assistant and routing the physical side key to that assistant were different problems**.

**Scope warning:** The observed value 101 is Samsung-specific to this tested firmware. Do not assume it is the correct value on another device. On the tested phone, the value was restored after each experiment. Reboot and update persistence were not verified; a system change could restore Samsung's value.

## 6. The VoiceInteractionSessionService dead end

After SystemUI invoked the custom assistant, its main VoiceInteractionService was created and marked ready. Its session service, however, could not be started:

~~~text
Unable to start service Intent {
  act=android.service.voice.VoiceInteractionService
  cmp=com.app.assistant/.AssistantVoiceInteractionSessionService
} U=0: not found

Failed binding to voice interaction session service
~~~

The tests established that the class existed in the APK and DEX; the manifest and metadata named the same component; the expected BIND_VOICE_INTERACTION permission was declared; package queries could resolve the service; the app was installed and enabled; and no session lifecycle callback or process startup was observed. Adding a separate session process did not help.

A non-debuggable build did not help either. Because that build also differed in optimization and APK packaging details, its result should not be presented as a perfect one-variable controlled trial. It does establish that **debuggable=false was not sufficient** to fix the observed symptom.

The precise internal cause of “not found” was **never identified**. This log message is not, by itself, proof that the class file is missing or that the firmware enforces a special signing allowlist.

As a control, the installed ChatGPT Android app successfully bound its own VoiceInteractionSessionService and opened its assistant screen under the same standard power-button assistant behavior. That ruled out the overly broad claim that this firmware categorically prevented *all* third-party voice-interaction sessions.

Instead of repeatedly guessing at signatures, SDK versions, and OEM internals, the experiment switched architecture.

## 7. Breakthrough: the official ACTION_ASSIST Activity path

The [Android 16 Compatibility Definition, section 3.8.4](https://source.android.com/docs/compatibility/16/android-16-cdd) recognizes both an app implementing VoiceInteractionService and an Activity handling ACTION_ASSIST as valid assist-app approaches. The [Android roles documentation](https://source.android.com/docs/core/permissions/android-roles) also describes the Activity-based assistant route.

An isolated experiment removed VoiceInteractionService/SessionService registrations and provided an AssistActivity handling **android.intent.action.ASSIST**, which launched MainActivity.

With the assistant role set to this experimental app and the side-key behavior temporarily set to 5, the system recorded:

~~~text
DigitalAssistantApp=com.app.assistant.activityonly
InvocationType=Side button
AssistManager: startAssistInternal

START ... act=android.intent.action.ASSIST
         cmp=com.app.assistant.activityonly/com.app.assistant.AssistActivity
         from com.android.systemui

START com.app.assistant.activityonly/com.app.assistant.MainActivity
~~~

**It worked.** The assistant main screen became the foreground Activity, without crash or ANR.

The proven path was then migrated to the original **com.app.assistant** package, whose final binary manifest kept ACTION_ASSIST and removed the VoiceInteractionService, VoiceInteractionSessionService, and placeholder RecognitionService registrations. On-device logs confirmed the same successful chain for the main app:

~~~text
DigitalAssistantApp=com.app.assistant
InvocationType=Side button
AssistManager: startAssistInternal

START ... act=android.intent.action.ASSIST
         cmp=com.app.assistant/.AssistActivity

START com.app.assistant/.MainActivity
~~~

This was a genuine **system-assistant invocation initiated by SystemUI**—not a side-key double-tap shortcut or an accessibility interception technique.

The Activity could also pass a flag requesting a single speech-input attempt. A UI launch and recognition attempt were observed, but successful transcription was still unproven.

## 8. Cloud speech recognition: conventional Android bugs, then HTTP 401

Cloud speech recognition was introduced as a fallback, using a user-configured endpoint. The tested service candidate was SiliconFlow with the model identifier **FunAudioLLM/SenseVoiceSmall**. The prototype recorded a short user-triggered mono WAV/PCM clip (16 kHz, 16-bit), capped at approximately 15 seconds; these were **application settings**, not a verified service-side maximum.

The first live attempt uncovered a separate application error:

~~~text
Configured speech recognition failed: NetworkOnMainThreadException
~~~

A synchronous HTTP operation had run on the Android main thread. Moving transcription to an IO dispatcher eliminated that defect.

Subsequent phone tests confirmed recording activity and network attempts. Initially, a generic IOException obscured the HTTP result; a diagnostic build was then changed to log only a sanitized response status. Multiple later requests returned:

~~~text
Configured speech recognition failed: STT HTTP 401
~~~

The locally entered key was replaced during controlled tests, but the outcome remained 401. No secret key, authorization header, voice sample, or raw HTTP body is included here.

**401 means the configured request was rejected at the HTTP authentication/authorization layer.** It does not establish *why*: key validity, service/account choice, account or model access, incorrect header construction, or another provider-side condition were not independently isolated. Repeated phone-side transcription attempts had little further diagnostic value without first verifying credentials in a separate test environment.

No successful transcript was received. Therefore the planned **spoken Chinese → STT → local command → Calculator** flow never passed, nor did full LLM chat, search citations, TTS, or voice-based alarm creation.

The earlier **typed** Chinese command did launch Calculator; that narrower result should not be mistaken for successful spoken control.

## 9. What was actually proven?

| Capability | Status |
| --- | --- |
| Recognition as an Android assistant candidate | **Verified on device** |
| Side-key routing to the selected third-party assistant (temporary behavior 5) | **Verified on device** |
| SystemUI → ACTION_ASSIST → main app UI | **Verified on device** |
| Typed Chinese “Open Calculator” command | **Verified on device** |
| Actual microphone capture and release | **Observed on device** |
| Usable native third-party Chinese STT on this firmware | **Not available in tested configuration** |
| VoiceInteractionSessionService implementation | **Failed; cause unresolved** |
| Configured cloud speech transcription | **Failed with HTTP 401** |
| Spoken Chinese command executing a phone action | **Not achieved** |
| Real LLM conversation, web search with sources, spoken response | **Not end-to-end verified** |
| Stable assistant configuration through reboot and system updates | **Not verified** |
| Everyday fully functional replacement for the stock assistant | **Not achieved** |

## 10. Engineering lessons worth sharing

1. **Distinguish assistant role selection from physical-key routing.** One can work while the other is vendor-specific.
2. **Use supported platform alternatives before reverse-engineering private services.** An ACTION_ASSIST Activity was sufficient for the successful hardware launch path.
3. **Treat “not found” as a symptom, not a root-cause diagnosis.** Component discovery and system-side binding are not identical checks.
4. **Use a positive platform control.** A working third-party assistant on the same phone prevented an unjustified “all third-party assistants are blocked” conclusion.
5. **Test each voice-processing boundary separately:** permission → capture → WAV encoding → network thread → HTTP transport → authorization → transcript → command execution.
6. **Never perform synchronous network calls on the UI thread.** That problem was ordinary Android application behavior, unrelated to Samsung's side-key policy.
7. **Do not equate green unit tests with working voice UX.** The later build passed 33 local tests but still could not transcribe a spoken command.
8. **Preserve a rollback for every settings experiment.** Before changing an assistant role or global power-key behavior, record the current value and restore it afterward.

## 11. Cautious reproducibility notes

These commands are illustrative for developer-controlled devices, **not** a universal Samsung fix:

~~~sh
# Read-only diagnostics
adb shell settings get global power_button_long_press
adb shell settings get global function_key_config_longpress_selected_item
adb shell cmd role get-role-holders --user 0 android.app.role.ASSISTANT

# Reversible experiment ONLY after recording original settings
adb shell settings put global power_button_long_press 5

# Example rollback ONLY if the observed original value was 101
adb shell settings put global power_button_long_press 101
~~~

If the original setting was absent, restore absence rather than substituting a guessed numeric default. Restoring the original assistant role is a separate step. Changing power-button configuration can alter expected power-menu behavior. Test on your own device at your own risk.

No root or firmware modification was used in the successful experiment, but **ADB authorization was needed to change the lower-level setting**. The report does not establish persistence across reboot. It also does not recommend binding to Samsung's protected ASR services or bypassing Android permission boundaries.

## 12. Final outcome

The original plan was a Chinese-language, conversational replacement for the default Samsung side-key AI experience.

**The system-integration challenge was partially solved:** the stock Android assistant Activity route really did launch a custom app from the physical side key on a China-market Galaxy S24.

**The voice-assistant product was not completed:** the tested speech-to-text API rejected repeated requests, the reason was not resolved, and no full spoken-command or spoken-answer loop passed.

The experiment is **paused**. Its useful contribution is the documented separation of Samsung hardware routing, Android assistant lifecycle, local command execution, audio capture, cloud authentication, and language-model functionality.

If resumed, a focused next step would be to confirm the chosen STT service's credentials and model authorization **outside the phone app** before attempting one more on-device end-to-end transcription. There is no reason to re-open the unsuccessful session-service approach merely to obtain the already proven Activity-only launch path.

**Affiliation and privacy:** This independent account describes technical behavior only. It is not affiliated with Samsung, Google, OpenAI, SiliconFlow, or any open-source project mentioned. It contains no personal identity details, local machine paths, unredacted device logs, APK files, speech recordings, or API credentials.

## References

- [Android 16 Compatibility Definition: Assist APIs](https://source.android.com/docs/compatibility/16/android-16-cdd)
- [Android Open Source Project: Android roles](https://source.android.com/docs/core/permissions/android-roles)
- [AOSP: assistant long-press behavior value](https://android.googlesource.com/platform/packages/apps/Settings/+/d2b251ec361/src/com/android/settings/gestures/PowerMenuSettingsUtils.java)
- [SideKey: Samsung One UI side-key investigation](https://github.com/quinnjr/sidekey)
- [Android developers: VoiceInteractionService reference](https://developer.android.com/reference/android/service/voice/VoiceInteractionService)
- [SiliconFlow: audio transcription API documentation](https://docs.siliconflow.cn/docs/api/audio-transcriptions-post)

---

*Evidence standard: this public report includes only anonymized excerpts and bounded test outcomes. It does not disclose private user data or claim that untested assistant features worked.*
