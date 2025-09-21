from google import genai

def creale_client(api_key: str):
    return genai.Client(api_key = api_key)

def request(prompt: str, api_key: str) -> str:
     client = creale_client(api_key)

     resp = client.models.generate_content(
         model="gemini-2.5-flash",
         contents=prompt
     )
     return resp.text
