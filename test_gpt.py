from openai import OpenAI

client = OpenAI(
  api_key="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"
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  store=True,
  messages=[
    {"role": "user", "content": "write a haiku about ai"}
  ]
)

print(completion.choices[0].message);
