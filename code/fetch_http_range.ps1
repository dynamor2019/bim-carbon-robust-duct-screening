param([Parameter(Mandatory=$true)][string]$RequestFile)
$ErrorActionPreference='Stop'
$spec=Get-Content -Raw -LiteralPath $RequestFile | ConvertFrom-Json
$client=[System.Net.Http.HttpClient]::new()
$client.Timeout=[TimeSpan]::FromMinutes(5)
$request=[System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get,[string]$spec.url)
$request.Headers.Range=[System.Net.Http.Headers.RangeHeaderValue]::new([long]$spec.start,[long]$spec.end)
$request.Headers.TryAddWithoutValidation('If-Match',[string]$spec.etag) | Out-Null
$response=$client.SendAsync($request,[System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
try {
    if ([int]$response.StatusCode -ne 206) { throw "Expected partial response, received $([int]$response.StatusCode); body not downloaded" }
    $range=$response.Content.Headers.ContentRange
    if ($range.From -ne [long]$spec.start -or $range.To -ne [long]$spec.end -or $range.Length -ne [long]$spec.total) { throw 'Content-Range mismatch' }
    if ($response.Headers.ETag.ToString() -ne [string]$spec.etag) { throw 'Remote archive ETag changed' }
    $inputStream=$response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $outputStream=[System.IO.File]::Create([string]$spec.output)
    try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose(); $inputStream.Dispose() }
    if ((Get-Item -LiteralPath $spec.output).Length -ne ([long]$spec.end-[long]$spec.start+1)) { throw 'Downloaded range length mismatch' }
} finally { $response.Dispose(); $request.Dispose(); $client.Dispose() }
