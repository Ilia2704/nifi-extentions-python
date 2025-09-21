from google import genai

api_key = "AIzaSyAo8AuWdvYOLfcA8IuL4LgWa8UyoonbI0g"

client = genai.Client(api_key = api_key)

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Скажи 'ok' и назови свой модельный идентификатор. После этого скажи 'привет мир' на русском языке."
)
print(resp.text)
