document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const teacherActionNote = document.getElementById("teacher-action-note");
  const teacherLoginToggle = document.getElementById("teacher-login-toggle");
  const teacherLoginPanel = document.getElementById("teacher-login-panel");
  const teacherLoginForm = document.getElementById("teacher-login-form");
  const teacherSession = document.getElementById("teacher-session");
  const teacherSessionLabel = document.getElementById("teacher-session-label");
  const teacherLogoutButton = document.getElementById("teacher-logout-button");
  const authState = {
    authenticated: false,
    username: null,
  };

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateTeacherUI() {
    teacherLoginToggle.classList.toggle("hidden", authState.authenticated);
    teacherSession.classList.toggle("hidden", !authState.authenticated);
    signupForm.classList.toggle("hidden", !authState.authenticated);
    teacherActionNote.classList.toggle("hidden", authState.authenticated);

    if (authState.authenticated) {
      teacherLoginPanel.classList.add("hidden");
      teacherLoginPanel.setAttribute("aria-hidden", "true");
      teacherLoginToggle.setAttribute("aria-expanded", "false");
      teacherSessionLabel.textContent = `Logged in as ${authState.username}`;
    } else {
      teacherSessionLabel.textContent = "";
    }
  }

  async function fetchTeacherSession() {
    try {
      const response = await fetch("/teacher/session");
      if (!response.ok) {
        throw new Error("Failed to load teacher session");
      }

      const session = await response.json();
      authState.authenticated = session.authenticated;
      authState.username = session.username;
      updateTeacherUI();
    } catch (error) {
      authState.authenticated = false;
      authState.username = null;
      updateTeacherUI();
      throw error;
    }
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML =
        '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        authState.authenticated
                          ? `<button type="button" class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  teacherLoginToggle.addEventListener("click", () => {
    teacherLoginPanel.classList.toggle("hidden");
    const expanded = !teacherLoginPanel.classList.contains("hidden");
    teacherLoginToggle.setAttribute("aria-expanded", String(expanded));
    teacherLoginPanel.setAttribute("aria-hidden", String(!expanded));
  });

  teacherLoginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("teacher-username").value;
    const password = document.getElementById("teacher-password").value;

    try {
      const response = await fetch("/teacher/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();

      if (response.ok) {
        teacherLoginForm.reset();
        await fetchTeacherSession();
        await fetchActivities();
        showMessage(result.message, "success");
      } else {
        showMessage(result.detail || "Teacher login failed", "error");
      }
    } catch (error) {
      showMessage("Failed to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  teacherLogoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/teacher/logout", {
        method: "POST",
      });
      const result = await response.json();

      if (response.ok) {
        await fetchTeacherSession();
        await fetchActivities();
        showMessage(result.message, "success");
      } else {
        showMessage(result.detail || "Teacher logout failed", "error");
      }
    } catch (error) {
      showMessage("Failed to log out. Please try again.", "error");
      console.error("Error logging out:", error);
    }
  });

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to register the student. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  fetchTeacherSession()
    .catch((error) => {
      console.error("Error loading teacher session:", error);
    })
    .finally(() => {
      fetchActivities().catch((error) => {
        console.error("Error loading activities:", error);
      });
    });
});
