document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            // Correctly get values from the form
            const username = document.getElementById("username").value;
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            try {
                // Send request to the correct endpoint: /users/
                const response = await fetch("/users/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ username, email, password }),
                });

                if (!response.ok) {
                    // Get error details from the response body if available
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Registration failed");
                }

                // If successful, redirect to the login page
                window.location.href = "/login";
                alert("Registration successful! Please log in.");

            } catch (error) {
                console.error("Registration Error:", error);
                alert(`Registration failed: ${error.message}`);
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;

            // The /token endpoint expects form data, not JSON
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            try {
                const response = await fetch("/token", {
                    method: "POST",
                    headers: {
                        // This header is important for form data
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    body: formData,
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Login failed");
                }

                const data = await response.json();

                // Store the token in localStorage
                localStorage.setItem("access_token", data.access_token);

                // Show success message and then redirect
                alert("Login successful!");
                window.location.href = "/";

            } catch (error) {
                console.error("Login Error:", error);
                alert(`Login failed: ${error.message}`);
            }
        });
    }
});
