import { Clerk } from '@clerk/clerk-js';

const publishableKey = 'pk_test_c3F1YXJlLWFscGFjYS0xNy5jbGVyay5hY2NvdW50cy5kZXYk';

async function initClerk() {
  const clerk = new Clerk(publishableKey);
  await clerk.load();

  if (!clerk.session) {
    await clerk.openSignIn({ redirectUrl: window.location.href, container: "#auth-container" });
    return;
  }

  document.getElementById("auth-container").innerHTML = `
    ✅ Signed in as: ${clerk.user.fullName}
  `;
  document.getElementById("controls").style.display = "block";

  document.getElementById("load-saml").addEventListener("click", async () => {
    const token = await clerk.session.getToken();
    const res = await fetch("http://localhost:8000/saml_config/", {
      headers: { Authorization: `Bearer ${token}` }
    });

    const data = await res.json();
    document.getElementById("output").textContent = JSON.stringify(data, null, 2);
  });

  window.Clerk = clerk;
}

document.addEventListener("DOMContentLoaded", initClerk);