import Cookies from "js-cookie";

export function saveTokens(accessToken: string, refreshToken: string) {
  Cookies.set("access_token", accessToken, { expires: 1 });       // 1 day
  Cookies.set("refresh_token", refreshToken, { expires: 7 });     // 7 days
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
}

export function isAuthenticated(): boolean {
  return !!Cookies.get("access_token");
}
