import { Clerk } from "@clerk/clerk-js";

const publishableKey = "pk_test_c3F1YXJlLWFscGFjYS0xNy5jbGVyay5hY2NvdW50cy5kZXYk";
let clerkInstance = null;

async function initClerk() {
  const clerk = new Clerk(publishableKey);
  await clerk.load();
  clerkInstance = clerk;

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

  const loaddataButton = document.getElementById("load-profile");
  if (loaddataButton) {
    loaddataButton.addEventListener("click", async () => { 
      const out = document.getElementById("profile-output");
      out.textContent = "⏳ Loading profile....";

      try {

        const token = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/clerk_jwt/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = "❌ " + err.message;
      }
    });
  }

  // Show SSO section if user has permissions
  const ssoSection = document.getElementById("sso-section");
  if (ssoSection) {
    // Check if user has SSO permissions
    try {
      
      const token = await session.getToken({ template: "full_user_token" });
      const res = await fetch("http://localhost:8000/settings/sso/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log("SSO permissions check response:", res.status);
      if (res.ok) {
        ssoSection.style.display = "block";
        // Load SAML connections immediately
        await loadSAMLConnections();
      } else {
        console.error("SSO permissions check failed:", await res.text());
      }
    } catch (err) {
      console.error("Error checking SSO permissions:", err);
    }
  }

  document.getElementById("sign-out").addEventListener("click", async () => {
    await clerk.signOut();
    window.location.reload();
  });

  // Tab functionality
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabId = button.getAttribute('data-tab');
      
      // Update active states
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(content => content.classList.remove('active'));
      
      button.classList.add('active');
      document.getElementById(`${tabId}-tab`).classList.add('active');
    });
  });

  // Load org members
  const loadMembersButton = document.getElementById("load-members");
  if (loadMembersButton) {
    loadMembersButton.addEventListener("click", async () => {
      const out = document.getElementById("members-output");
      out.textContent = "⏳ Loading members…";

      try {
        const token = await session.getToken({ template: "full_user_token" });
        const res = await fetch("http://localhost:8000/settings/org-members/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = "❌ " + err.message;
      }
    });
  }


  // Load SAML connections
  const loadSsoButton = document.getElementById("load-sso");
  if (loadSsoButton) {
    loadSsoButton.addEventListener("click", async () => {
      await loadSAMLConnections();
    });
  }

  // Add SAML connection
  const ssoForm = document.getElementById("sso-form");
  if (ssoForm) {
    ssoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      // Get form values directly from input elements
      const name = document.getElementById('sso-name').value;
      const domain = document.getElementById('sso-domain').value;
      const metadata_url = document.getElementById('sso-metadata-url').value;
      const provider = document.getElementById('sso-provider')?.value || 'saml_custom';
      
      const data = {
        name,
        domain,
        metadata_url,
        provider
      };

      try {
          const token = await clerkInstance.session.getToken({ template: "full_user_token" });
          console.log("Submitting form data:", data);  // Debug log

          const response = await fetch('http://localhost:8000/settings/sso/create/', {
              method: 'POST',
              headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
          });

          console.log("Response status:", response.status);  // Debug log
          const result = await response.json();
          console.log("Response data:", result);  // Debug log

          if (response.ok) {
              // Show success message
              const successMessage = document.createElement('div');
              successMessage.className = 'toast success';
              successMessage.textContent = 'SAML connection created successfully';
              document.body.appendChild(successMessage);
              setTimeout(() => successMessage.remove(), 3000);

              // Close modal and refresh connections
              const modal = document.getElementById('sso-modal');
              modal.classList.remove('active');
              ssoForm.reset();
              await loadSAMLConnections();
          } else {
              // Show error message
              const errorMessage = document.createElement('div');
              errorMessage.className = 'toast error';
              errorMessage.textContent = result.error?.detail || 'Failed to create SAML connection';
              document.body.appendChild(errorMessage);
              setTimeout(() => errorMessage.remove(), 3000);
          }
      } catch (error) {
          console.error('Error:', error);
          // Show error message
          const errorMessage = document.createElement('div');
          errorMessage.className = 'toast error';
          errorMessage.textContent = 'Failed to create SAML connection';
          document.body.appendChild(errorMessage);
          setTimeout(() => errorMessage.remove(), 3000);
      }
    });
  }

  // Copy button functionality
  document.querySelectorAll('.copy-button').forEach(button => {
    button.addEventListener('click', () => {
      const inputId = button.getAttribute('data-copy');
      const input = document.getElementById(inputId);
      input.select();
      document.execCommand('copy');
      button.textContent = 'Copied!';
      setTimeout(() => {
        button.textContent = 'Copy';
      }, 2000);
    });
  });
}

// Global functions for connection actions
window.toggleConnection = async (connectionId, enable) => {
  if (!clerkInstance) {
    alert("Session expired. Please refresh the page.");
    return;
  }

  try {
    const token = await clerkInstance.session.getToken({ template: "full_user_token" });
    const res = await fetch(`http://localhost:8000/settings/sso/${connectionId}/toggle/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ active: enable }),
    });
    
    if (res.ok) {
      // Refresh the connections list
      document.getElementById("load-sso").click();
    } else {
      alert("Failed to update connection status");
    }
  } catch (err) {
    alert("❌ " + err.message);
  }
};

window.editConnection = async (connectionId) => {
  if (!clerkInstance) {
    alert("Session expired. Please refresh the page.");
    return;
  }
  // Implement edit functionality
  alert("Edit functionality coming soon!");
};

window.deleteConnection = async function(connectionId) {
  if (!clerkInstance) {
    alert("Session expired. Please refresh the page.");
    return;
  }

  // Create and show a custom confirmation dialog
  const connection = connections.find(c => c.id === connectionId);
  if (!connection) {
    console.error("Connection not found:", connectionId);
    alert("Connection not found. Please refresh the page and try again.");
    return;
  }

  const confirmDialog = document.createElement('div');
  confirmDialog.className = 'modal active';
  confirmDialog.innerHTML = `
    <div class="modal-content" style="max-width: 400px;">
      <div class="modal-header">
        <h3>Delete SAML Connection</h3>
        <button class="close-modal" onclick="this.closest('.modal').remove()">&times;</button>
      </div>
      <div style="padding: var(--spacing-md);">
        <p>Are you sure you want to delete the SAML connection "${connection.name}"?</p>
        <p style="color: var(--c-text-light); font-size: 0.9rem;">This action cannot be undone.</p>
        <div class="form-actions" style="margin-top: var(--spacing-md);">
          <button class="secondary-button" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="primary-button" style="background: #dc2626;" onclick="confirmDelete('${connectionId}', this)">Delete Connection</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(confirmDialog);
};

// Separate function to handle the actual deletion
window.confirmDelete = async function(connectionId, button) {
  try {
    // Disable the button and show loading state
    button.disabled = true;
    button.textContent = 'Deleting...';
    
    const token = await clerkInstance.session.getToken({ template: "full_user_token" });
    console.log("Attempting to delete connection:", connectionId);
    
    const response = await fetch(`http://localhost:8000/settings/sso/delete/${connectionId}/`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });

    

    // Remove the modal
    button.closest('.modal').remove();

    if (response.ok) {
      // Show success message
      const successMessage = document.createElement('div');
      successMessage.className = 'toast success';
      successMessage.textContent = 'SAML connection deleted successfully';
      document.body.appendChild(successMessage);
      setTimeout(() => successMessage.remove(), 3000);

      // Refresh the connections list
      await window.loadSAMLConnections();
    } else {
      const error = await response.json();
      console.error("Delete error:", error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'toast error';
      errorMessage.textContent = error.detail || 'Failed to delete connection';
      document.body.appendChild(errorMessage);
      setTimeout(() => errorMessage.remove(), 3000);
    }
  } catch (error) {
    console.error('Error:', error);
    // Show error message
    const errorMessage = document.createElement('div');
    errorMessage.className = 'toast error';
    errorMessage.textContent = 'Failed to delete connection';
    document.body.appendChild(errorMessage);
    setTimeout(() => errorMessage.remove(), 3000);
  }
};

// Global variables
let connections = [];

// Make loadSAMLConnections globally available
window.loadSAMLConnections = async function() {
  try {
    console.log("Loading SAML connections...");
    const token = await clerkInstance.session.getToken({ template: "full_user_token" });
    const response = await fetch('http://localhost:8000/settings/sso/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });
    
    console.log("SAML connections response status:", response.status);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log("SAML connections data:", data);
    
    const connectionsList = document.getElementById('connections-list');
    if (!connectionsList) {
      console.error("connections-list element not found");
      return;
    }
    
    if (!data || !data.connections) {
      console.error("No connections data received");
      connectionsList.innerHTML = "No SAML connections found.";
      return;
    }

    // Store connections globally
    connections = data.connections;
    
    connectionsList.innerHTML = connections.map(connection => `
      <div class="connection-item">
        <h4>${connection.name}</h4>
        <p><strong>Domain:</strong> ${connection.domain}</p>
        <p><strong>Status:</strong> ${connection.active ? 'Active' : 'Inactive'}</p>
        <p><strong>Created:</strong> ${new Date(connection.created_at).toLocaleDateString()}</p>
        
        <div class="connection-details">
          <h5>Identity Provider</h5>
          <p><strong>Entity ID:</strong> ${connection.identity_provider?.entity_id || 'Not configured'}</p>
          <p><strong>SSO URL:</strong> ${connection.identity_provider?.sso_url || 'Not configured'}</p>
          <p><strong>Metadata URL:</strong> ${connection.identity_provider?.metadata_url || 'Not configured'}</p>
        </div>

        <div class="connection-details">
          <h5>Service Provider</h5>
          <p><strong>Entity ID:</strong> ${connection.service_provider?.entity_id || 'Not configured'}</p>
          <p><strong>ACS URL:</strong> ${connection.service_provider?.acs_url || 'Not configured'}</p>
          <p><strong>Metadata URL:</strong> ${connection.service_provider?.metadata_url || 'Not configured'}</p>
        </div>

        <div class="connection-actions">
          <button class="secondary-button" onclick="toggleConnection('${connection.id}', ${!connection.active})">
            ${connection.active ? 'Disable' : 'Enable'}
          </button>
          <button class="secondary-button" onclick="editConnection('${connection.id}')">Edit</button>
          <button class="secondary-button" onclick="deleteConnection('${connection.id}')">Delete</button>
          <button class="secondary-button" onclick="showSPConfig('${connection.id}')">View SP Config</button>
        </div>
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading SAML connections:', error);
    alert('Failed to load SAML connections');
  }
};

// Close modal function
window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
    }
  }
};

// Show Service Provider Configuration
window.showSPConfig = function(connectionId) {
  const modal = document.getElementById('sp-config-modal');
  const connection = connections.find(c => c.id === connectionId);
  
  if (connection) {
    document.getElementById('sp-acs-url').value = connection.service_provider?.acs_url || '';
    document.getElementById('sp-entity-id').value = connection.service_provider?.entity_id || '';
    document.getElementById('sp-metadata-url').value = connection.service_provider?.metadata_url || '';
    modal.classList.add('active');
  }
};

// Initialize the page
document.addEventListener('DOMContentLoaded', async () => {
  const addConnectionBtn = document.getElementById('add-connection');
  const modal = document.getElementById('sso-modal');
  const closeModal = document.querySelector('.close-modal');
  const ssoForm = document.getElementById('sso-form');
  const connectionsList = document.getElementById('connections-list');
  const editModal = document.getElementById('edit-modal');
  const editForm = document.getElementById('edit-form');
  const closeEditModal = document.querySelector('.close-edit-modal');
  if (closeEditModal) {
    closeEditModal.addEventListener('click', () => {
      editModal.classList.remove('active');
      editForm.reset();
    });
  }

  // Load SAML connections on page load
  await loadSAMLConnections();

  // Add new connection
  addConnectionBtn.addEventListener('click', () => {
    modal.classList.add('active');
  });

  // Close modals
  closeModal.addEventListener('click', () => {
    modal.classList.remove('active');
    ssoForm.reset();
  });

  closeEditModal.addEventListener('click', () => {
    editModal.classList.remove('active');
    editForm.reset();
  });

  // Handle form submission
  ssoForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(ssoForm);
    const data = {
      name: formData.get('name'),
      domain: formData.get('domain'),
      idp_metadata_url: formData.get('idp_metadata_url'),
      attribute_mapping: formData.get('attribute_mapping')
    };

    try {
      const response = await fetch('/api/saml/connections/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        modal.classList.remove('active');
        ssoForm.reset();
        await loadSAMLConnections();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create SAML connection');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to create SAML connection');
    }
  });

  // Handle edit form submission
  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(editForm);
    const connectionId = editForm.dataset.connectionId;
    const data = {
      name: formData.get('name'),
      domain: formData.get('domain'),
      idp_metadata_url: formData.get('idp_metadata_url'),
      attribute_mapping: formData.get('attribute_mapping')
    };

    try {
      const response = await fetch(`/api/saml/connections/${connectionId}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        editModal.classList.remove('active');
        editForm.reset();
        await loadSAMLConnections();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to update SAML connection');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to update SAML connection');
    }
  });

  // Add event listeners for modal close buttons
  document.querySelectorAll('.close-modal').forEach(button => {
    button.addEventListener('click', () => {
      const modal = button.closest('.modal');
      if (modal) {
        closeModal(modal.id);
      }
    });
  });
});

document.addEventListener("DOMContentLoaded", async () => {
  await initClerk(); // this ensures clerkInstance is set and session is ready
});