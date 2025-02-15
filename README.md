# Ai-Assistant

This is a project to setup your very Ai Assistant using OpenAi.

### Installation

1. Install packages using `pip install -r requirements.txt` in the root directory
   Note that you will need `Visual C++ Build Tool` for `simpleaudio`. Ensure you have installed the correct components of the Microsoft Build Tools.
   For Visual Studio 2022, follow these steps to install a required packages for `Visual C++ Build Tool`:

    - Open the Visual Studio Installer.
    - Click on Modify for your Visual Studio 2022 installation.
    - Go to the Workloads tab.
    - Under Desktop Development with C++, ensure you have selected:
        - MSVC v143 - VS 2022 C++ x64/x86 build tools [today's latest]
        - C++ CMake tools for Windows
        - Go to the Individual Components tab and check the following: Windows 10/11 SDK (latest version) [normally the latest in the list]
        - C++/CLI support
    - Apply the changes and wait for the installation to complete.

2. Get a OpenAI API Key at [OpenAPIKey](https://openai.com/api/)
3. Rename `.env.example` to `.env` and enter API Keys:

    ```sh
    OPENAI_API_KEY="Your OpenAI API Key"
    ```

4. Run

    ```sh
    python Voice_GPT.py
    ```

### Some information for dumpshitty guys like me

(Note that these information are just assumptions, to explain for myself how certain things will work
so some of them could be wrong)

So when it comes to realtime usage there are a couple of things to consider:

-   know what audio input and output openAI want (e.g. `pcm16`)
    this is good to know especially if it comes to some trouble shooting with problems like:
    -   why the fck will my websocket not return any thing after I send an event?
    -   why will I get some chopped unknown sentences from openAI (e.g. when transcribing from audio to text)
    -   why are the mic settings as they are?
    -   why is my ai talking so damn slow
-   know the some event "cycles",
    so you don't have to learn the whole API from openAI, but it could be a big benefit to know what event
    you will be received, if you sende e.g. a `input_audio_buffer.append` or a `conversation.item.create`
    event, also the API of openAI is well documented and you can read what event will trigger what. Sometimes
    it can also help to debug the `event_type` in my `receive_audio_from_websocket()`
-   when working with the library `speech_recognition` it's good to know that the callback function
    (especially with filter etc.) will work like some sort of "push to talk" so because
    the library is so got in filtering audio, your `mic_queue` will only contains words and barely "silence parts".
    This is good to know, because if you use the VAD Server from openAI, it will listen to silence parts to kow
    when a sentence is "over", but if there is no silence VAD will never end since it will wait for a silence part
    to send the `input_audio_buffer.commit` automatically.
-   Speaking of VAD (Voice Activity Detection) its just some high technology shit form openAI, which will detect
    if you're speaking or not, you can also use your own VAD, but I'm to dump to know how. The VAD can be
    "activated" and "deactivated" in the `session.update`/ `session.create` event by using
    (`turn_detection: {something: something}`) or not using (`turn_detection: None`) the `turn_detection` object.
-   when you're trying to use some fancy "local" transcription Model (like `faster-whisper`), note that you have to
    have a "highend PC" to actually be faster than openAI's Whisper Model. If you have a shitty pc like me I would
    prefere using the API, but if you're a game and have a highend PC you could try the local library `faster-whisper`
