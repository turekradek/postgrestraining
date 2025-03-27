select * from webscraping.schedule
WHERE plan_id = '20'  --'20'
  AND retailer_spec_id = '38'
  and schedule_type = 'deepscrape'
  AND keyword_id IN (SELECT id FROM webscraping.keyword WHERE keyword IN (SELECT keyword FROM webscraping.deep_scraping_kw_5));
