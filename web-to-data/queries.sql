
-- select accessible pages

SELECT 
  JSON_EXTRACT_SCALAR(report, "$.categories.accessibility.score") as accessibilityScore,
  url,
  FROM `httparchive.sample_data.lighthouse_mobile_1k`  
ORDER BY 1 
DESC LIMIT 1000

-- get HTML url contents from websites

SELECT url, body FROM `httparchive.sample_data.response_bodies_desktop_1k` 
  WHERE page = url AND url NOT LIKE '%.jp/' AND body NOT LIKE '%lang="ja"%'
LIMIT 1000

-- get languages from websites

SELECT COUNT(*) as cnt, REGEXP_EXTRACT(body, r'lang=[\'"]?([^ "\'>]{2,7})[\'"]?') as lang FROM `httparchive.sample_data.response_bodies_desktop_1k` 
  WHERE page = url AND REGEXP_EXTRACT(body, r'lang=[\'"]?([^ "\'>]{2,7})[\'"]?') is not null
GROUP BY lang
ORDER BY cnt DESC
LIMIT 1000


'-- compound query not working
SELECT 
  JSON_EXTRACT_SCALAR(report, "$.categories.accessibility.score") as accessibilityScore,
  url as pageUrl,
  (SELECT body FROM `httparchive.sample_data.response_bodies_mobile_1k` as response_bodies
  WHERE lighthouse.url = response_bodies.url AND url NOT LIKE '%.jp/' AND body NOT LIKE '%lang="ja"%' LIMIT 1) as html
FROM `httparchive.sample_data.lighthouse_mobile_1k` as lighthouse 
ORDER BY 1 
DESC LIMIT 1000

-- query working

SELECT 
  JSON_EXTRACT_SCALAR(report, "$.categories.accessibility.score") as accessibilityScore,
  url as pageUrl,
  bodies.body
FROM `httparchive.sample_data.lighthouse_mobile_1k` as lighthouse 
JOIN `httparchive.sample_data.response_bodies_mobile_1k` as bodies using (url)
WHERE 
  bodies.truncated = False AND
  REGEXP_EXTRACT(LOWER(bodies.body), r'lang=[\'"]?([^ "\'>]{2,7})[\'"]?') LIKE 'en%' AND 
  LOWER(bodies.body) like '%aria%'
ORDER BY accessibilityScore DESC

"
-- query on real data working
SELECT 
  JSON_EXTRACT_SCALAR(report, "$.categories.accessibility.score") as accessibilityScore,
  url as pageUrl,
  bodies.body
FROM `httparchive.latest.lighthouse_mobile` as lighthouse 
JOIN `httparchive.latest.response_bodies_mobile` as bodies using (url)
WHERE 
  bodies.truncated = False AND
  REGEXP_EXTRACT(LOWER(bodies.body), r'lang=[\'"]?([^ "\'>]{2,7})[\'"]?') LIKE 'en%' AND 
  LOWER(bodies.body) like '%aria%'
ORDER BY accessibilityScore DESC
