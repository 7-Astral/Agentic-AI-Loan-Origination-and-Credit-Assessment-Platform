import { redirect } from "next/navigation";

// Single-tenant dev convenience: the only seeded bank today is demo-mutual. Once multiple
// banks exist, this should become a bank picker rather than a fixed redirect. Root goes to
// login rather than straight into the anonymous chat flow — the chat is still reachable
// from the login page or directly at /demo-mutual, but signing in is the primary path in.
export default function RootPage() {
  redirect("/demo-mutual/login");
}
