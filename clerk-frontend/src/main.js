import { Clerk } from "@clerk/clerk-js";

const publishableKey = "pk_test_c3F1YXJlLWFscGFjYS0xNy5jbGVyay5hY2NvdW50cy5kZXYk";

async function initClerk() {
  const clerk = new Clerk(publishableKey);
  await clerk.load();

  const ssoLoginSection = document.getElementById("sso-login-section");
  const ssoLink = document.getElementById("sso-login-link");

  if (!clerk.session) {
    if (ssoLoginSection && ssoLink) {
      ssoLoginSection.style.display = "block";
      ssoLink.href = "https://clerk.accounts.dev/saml/sso/samlc_2woruEGlhwtajYyi0Prc7Y94qBc/login";
    }

    clerk.openSignIn({
      afterSignInUrl: window.location.href,
      afterSignUpUrl: window.location.href,
    });
    return;
  }

  ssoLoginSection?.remove();

  const { user, session } = clerk;
  document.getElementById("auth-container").innerHTML = `
    ✅ Signed in as <strong>${user.primaryEmailAddress}</strong>
    <br /><button id="sign-out" type="button">🚪 Sign out</button>
  `;
  clerk.mountUserButton(document.getElementById("user-button"));
  document.getElementById("controls").style.display = "block";

  // Show SSO section if user has permissions
  const ssoSection = document.getElementById("sso-section");
  if (ssoSection) {
    // Check if user has SSO permissions
    try {
      const token = await session.getToken({ template: "full_user_token" });
      const res = await fetch("http://localhost:8000/settings/sso/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        ssoSection.style.display = "block";
      }
    } catch (err) {
      console.log("User doesn't have SSO permissions");
    }
  }

  document.getElementById("sign-out").addEventListener("click", async () => {
    await clerk.signOut();
    window.location.reload();
  });

  // Only add event listeners if elements exist
  const loadDataButton = document.getElementById("load-data");
  if (loadDataButton) {
    loadDataButton.addEventListener("click", async () => {
      const out = document.getElementById("output");
      out.textContent = "⏳ Fetching…";

      try {
        const token = await clerk.session.getToken({
          template: "full_user_token",
        });

        const r = await fetch("http://localhost:8000/clerk_jwt/", {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!r.ok) throw new Error(`Server returned ${r.status}`);
        out.textContent = JSON.stringify(await r.json(), null, 2);
      } catch (err) {
        out.textContent = "❌ " + err.message;
        console.error(err);
      }
    });
  }

  // Load org members
  const loadMembersButton = document.getElementById("load-members");
  if (loadMembersButton) {
    console.log("Load members button found:", true);
    
    loadMembersButton.addEventListener("click", async () => {
      console.log("Load members button clicked");
      const out = document.getElementById("members-output");
      console.log("Members output element found:", !!out);
      out.textContent = "⏳ Loading members…";

      try {
        console.log("Getting fresh token...");
        const freshToken = await session.getToken({ template: "full_user_token" });
        console.log("Making API request...");
        const res = await fetch("http://localhost:8000/settings/org-members/", {
          headers: { Authorization: `Bearer ${freshToken}` },
        });
        console.log("API response status:", res.status);
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);

        // Populate dropdown
        const select = document.getElementById("break-glass-user-select");
        if (select) {
          select.innerHTML = '<option disabled selected>Select member email</option>';
          data.members.forEach((member) => {
            const option = document.createElement("option");
            option.value = member.email;
            option.textContent = member.email;
            select.appendChild(option);
          });
        }
      } catch (err) {
        console.error("Error in load-members:", err);
        out.textContent = "❌ " + err.message;
      }
    });
  }

  // Load break-glass users
  const loadBreakGlassButton = document.getElementById("load-break-glass");
  if (loadBreakGlassButton) {
    loadBreakGlassButton.addEventListener("click", async () => {
      const out = document.getElementById("break-glass-output");
      out.textContent = "⏳ Loading break-glass users...";
      try {
        const freshToken = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/settings/break-glass/", {
          headers: { Authorization: `Bearer ${freshToken}` },
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = "❌ " + err.message;
      }
    });
  }

  // Add break-glass user
  const addBreakGlassButton = document.getElementById("add-break-glass");
  if (addBreakGlassButton) {
    addBreakGlassButton.addEventListener("click", async () => {
      const email = document.getElementById("break-glass-user-select")?.value;
      if (!email) return alert("Please select a user");

      try {
        const freshToken = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/settings/break-glass/create/", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${freshToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        });

        const data = await res.json();
        alert("✅ Added: " + data.email);
      } catch (err) {
        alert("❌ " + err.message);
      }
    });
  }

  // Load SAML connections
  const loadSsoButton = document.getElementById("load-sso");
  if (loadSsoButton) {
    loadSsoButton.addEventListener("click", async () => {
      const out = document.getElementById("sso-output");
      out.textContent = "⏳ Loading SAML connections…";
      try {
        const freshToken = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/settings/sso/", {
          headers: { Authorization: `Bearer ${freshToken}` },
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = "❌ " + err.message;
      }
    });
  }

  // Add SAML connection
  const addSsoButton = document.getElementById("add-sso");
  if (addSsoButton) {
    addSsoButton.addEventListener("click", async () => {
      const metadata_url = document.getElementById("sso-metadata-url").value;
      if (!metadata_url) {
        alert("Please enter a Metadata URL.");
        return;
      }

      try {
        const freshToken = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/settings/sso/create/", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${freshToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ metadata_url }),
        });

        const data = await res.json();
        alert(JSON.stringify(data, null, 2));
      } catch (err) {
        alert("❌ " + err.message);
      }
    });
  }
}


document.addEventListener("DOMContentLoaded", initClerk);