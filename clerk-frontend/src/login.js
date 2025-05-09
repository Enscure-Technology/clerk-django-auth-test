import { Clerk } from "@clerk/clerk-js";

const publishableKey = "pk_test_...";
const SAML_URL = "https://square-alpaca-17.clerk.accounts.dev/saml/sso/samlc_2woruEGlhwtajYyi0Prc7Y94qBc/login";

document.getElementById("login").addEventListener("click", async () => {
  const email = document.getElementById("email").value.trim();
  if (!email) return alert("Enter your email");

  document.getElementById("loading").style.display = "block";

  try {
    const res = await fetch("http://localhost:8000/is-break-glass/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const { is_break_glass } = await res.json();

    if (is_break_glass) {
      const clerk = new Clerk(publishableKey);
      await clerk.load();
      clerk.openSignIn({
        afterSignInUrl: "/",
        afterSignUpUrl: "/",
        identifier: email,
      });
    } else {
      window.location.href = SAML_URL;
    }
  } catch (err) {
    alert("❌ Error: " + err.message);
  }
});