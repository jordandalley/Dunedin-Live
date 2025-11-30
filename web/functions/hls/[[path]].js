export async function onRequest(context) {
  const backend = "https://dl-img.dalleyfamily.net";

  const url = new URL(context.request.url);

  // strip /hls from the front
  const suffix = url.pathname.replace(/^\/hls/, "");
  const targetPath = "/memfs" + suffix;
  const targetUrl = backend + targetPath + url.search;

  const response = await fetch(targetUrl, {
    method: context.request.method,
    headers: context.request.headers,
    body: context.request.body,
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}
