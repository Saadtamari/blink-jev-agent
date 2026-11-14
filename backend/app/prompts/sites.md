Always add the parameters that force English and US dollars where the site supports them (shown below), so prices come back in USD no matter where the computer is.

- Flights: Google Flights (first choice, results load directly):
  https://www.google.com/travel/flights?q=Flights%20from%20CAI%20to%20TYO%20on%202027-03-10%20through%202027-03-17&hl=en&gl=us&curr=USD
  fallback_urls: Kayak, then Skyscanner (both often show a bot check, so they come last):
  https://www.kayak.com/flights/CAI-TYO/2027-03-10/2027-03-17?currency=USD
  https://www.skyscanner.net/transport/flights/cai/tyoa/270310/270317/?adultsv2=1&currency=USD&locale=en-GB&market=UK
  extract target: "the list of flight results with prices"
- Hotels: Google Hotels:
  https://www.google.com/travel/search?q=hotels%20in%20Tokyo&checkin=2027-03-10&checkout=2027-03-17&hl=en&gl=us&curr=USD
  fallback_urls: Booking.com, then Hotels.com:
  https://www.booking.com/searchresults.en-us.html?ss=Tokyo&checkin=2027-03-10&checkout=2027-03-17&group_adults=1&no_rooms=1&selected_currency=USD
  https://www.hotels.com/Hotel-Search?destination=Tokyo&startDate=2027-03-10&endDate=2027-03-17&adults=1
  extract target: "the list of hotels with nightly prices"
- Visa rules: Wikipedia "Visa requirements for <nationality> citizens", e.g.
  https://en.wikipedia.org/wiki/Visa_requirements_for_Egyptian_citizens
  One extract step is enough (the extractor also reads the full page text): extract target "the table row for <country>".
- Daily living / travel costs: Numbeo (USD): https://www.numbeo.com/cost-of-living/in/Tokyo?displayCurrency=USD
  fallback_urls: https://www.budgetyourtrip.com/japan/tokyo
  extract target: "the table of prices for restaurants, transport and other items"
- Currency rates: https://wise.com/us/currency-converter/usd-to-egp-rate?amount=1  (lowercase codes; extract target: "the conversion result")
- Product prices: Amazon search https://www.amazon.com/s?k=<query>, eBay https://www.ebay.com/sch/i.html?_nkw=<query>
  fallback_urls for a store branch: Google Shopping https://www.google.com/search?tbm=shop&q=<query>&hl=en&gl=us
- General facts: Wikipedia https://en.wikipedia.org/wiki/<Title>
