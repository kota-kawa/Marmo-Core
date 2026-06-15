import { NextResponse } from "next/server";
import { auth } from "@/auth";

const PROTECTED_PREFIXES = ["/proposal", "/admin"];

export default auth((request) => {
  const { pathname, search } = request.nextUrl;
  const sessionUser = request.auth?.user;
  const isAuthenticated = Boolean(sessionUser);
  const isAuthPage = pathname === "/sign-in" || pathname === "/sign-up";
  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  const isAdminPage = pathname.startsWith("/admin");

  if (!isAuthenticated && isProtected) {
    const signInUrl = new URL("/sign-in", request.url);
    signInUrl.searchParams.set("callbackUrl", `${pathname}${search}`);
    return NextResponse.redirect(signInUrl);
  }

  if (isAuthenticated && isAuthPage) {
    return NextResponse.redirect(new URL("/proposal/new", request.url));
  }

  if (isAdminPage) {
    const role = sessionUser?.role ?? "RESEARCHER";
    if (role !== "ADMIN") {
      return NextResponse.redirect(new URL("/proposal/new", request.url));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)"],
};
