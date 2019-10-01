SELECT 
  JSON_EXTRACT_SCALAR(report, "$.categories.accessibility.score") as accessibilityScore,
  url as pageUrl,
  report as lighthouseAudit,
  bodies.body
FROM `httparchive.sample_data.lighthouse_mobile_10k` as lighthouse 
JOIN `httparchive.sample_data.response_bodies_mobile_10k` as bodies using (url)
WHERE 
  bodies.truncated = False AND
  REGEXP_EXTRACT(LOWER(bodies.body), r'lang=[\'"]?([^ "\'>]{2,7})[\'"]?') LIKE 'en%' AND 
  LOWER(bodies.body) like '%aria%'
ORDER BY accessibilityScore DESC