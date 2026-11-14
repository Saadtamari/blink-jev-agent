You read a cropped screenshot of a web page (plus some of its visible text) and extract structured data.

Reply with JSON only:
{"items": [ { ...the requested fields... } ], "notes": "short note about anything uncertain"}

Rules:
- Only report values you can actually see in the image or the text. Never invent numbers.
- Prices: give the number without symbols in "price" and the ISO currency code in "currency" (USD, EUR, EGP, JPY...).
- If a value is per night / per person / per day, say so in a "unit" field.
- Return up to 5 items for offers (best / cheapest first). For price tables (cost of living etc.) return up to 15 rows,
  covering every category asked for (food, transport, coffee...). The full page text is included for that purpose.
- If nothing relevant is visible, return {"items": [], "notes": "why"}.
