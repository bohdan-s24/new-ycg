// Handles auth UI rendering and error display
export function showAuthError(message) {
  const errorMessage = document.getElementById("error-message");
  if (errorMessage) {
    errorMessage.textContent = message;
    errorMessage.classList.remove("hidden");
  }
}

export function hideAuthError() {
  const errorMessage = document.getElementById("error-message");
  if (errorMessage) {
    errorMessage.classList.add("hidden");
  }
}
