import pyttsx3
import speech_recognition as sr
import time
from openai import OpenAI
from .credentials import OPENAI_API_KEY

openai = OpenAI(api_key=OPENAI_API_KEY)