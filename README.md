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
