Always add the parameters that force English and US dollars where the site supports them (shown below), so prices come back in USD no matter where the computer is.

- Flights: Google Flights with a direct query URL (results load directly):
  https://www.google.com/travel/flights?q=Flights%20from%20CAI%20to%20TYO%20on%202027-03-10%20through%202027-03-17&hl=en&gl=us&curr=USD
  extract target: "the list of flight results with prices"
- Hotels: Google Hotels search URL:
  https://www.google.com/travel/search?q=hotels%20in%20Tokyo&checkin=2027-03-10&checkout=2027-03-17&hl=en&gl=us&curr=USD
  extract target: "the list of hotels with nightly prices"
- Visa rules: Wikipedia "Visa requirements for <nationality> citizens", e.g.
  https://en.wikipedia.org/wiki/Visa_requirements_for_Egyptian_citizens
  The country table is long: add a "type" or "scroll" is NOT needed; instead extract target: "the table row for <country>".
  Better: use the in-page search URL form https://en.wikipedia.org/wiki/Visa_requirements_for_Egyptian_citizens#<Country> is not reliable, so just extract.
- Daily living / travel costs: Numbeo (USD): https://www.numbeo.com/cost-of-living/in/Tokyo?displayCurrency=USD
  extract target: "the table of prices for restaurants, transport and other items"
- Currency rates: https://www.x-rates.com/calculator/?from=USD&to=EGP&amount=1  (extract target: "the conversion result")
- Product prices: Amazon search https://www.amazon.com/s?k=<query>, eBay https://www.ebay.com/sch/i.html?_nkw=<query>
- General facts: Wikipedia https://en.wikipedia.org/wiki/<Title>
