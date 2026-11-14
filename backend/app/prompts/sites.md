Always add the parameters that force English and US dollars where the site supports them (shown below), so prices come back in USD no matter where the computer is.

- Flights: Skyscanner (preferred). Direct search URL, dates as YYMMDD, airport/city codes in lowercase:
  https://www.skyscanner.net/transport/flights/cai/tyoa/270310/270317/?adultsv2=1&cabinclass=economy&currency=USD&locale=en-GB&market=UK
  Skyscanner usually shows a "press and hold" bot check: the user solves it once, so ALWAYS also set
  "fallback_url" to the Google Flights URL for the same search:
  https://www.google.com/travel/flights?q=Flights%20from%20CAI%20to%20TYO%20on%202027-03-10%20through%202027-03-17&hl=en&gl=us&curr=USD
  extract target: "the list of flight results with prices"
- Hotels: Google Hotels search URL:
  https://www.google.com/travel/search?q=hotels%20in%20Tokyo&checkin=2027-03-10&checkout=2027-03-17&hl=en&gl=us&curr=USD
  extract target: "the list of hotels with nightly prices"
- Visa rules: Wikipedia "Visa requirements for <nationality> citizens", e.g.
  https://en.wikipedia.org/wiki/Visa_requirements_for_Egyptian_citizens
  One extract step is enough (the extractor also reads the full page text): extract target "the table row for <country>".
- Daily living / travel costs: Numbeo (USD): https://www.numbeo.com/cost-of-living/in/Tokyo?displayCurrency=USD
  extract target: "the table of prices for restaurants, transport and other items"
- Currency rates: https://wise.com/us/currency-converter/usd-to-egp-rate?amount=1  (lowercase codes; extract target: "the conversion result")
- Product prices: Amazon search https://www.amazon.com/s?k=<query>, eBay https://www.ebay.com/sch/i.html?_nkw=<query>
- General facts: Wikipedia https://en.wikipedia.org/wiki/<Title>
