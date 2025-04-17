// Lazy-loaded feedback module
export function openFeedbackForm() {
  chrome.tabs.create({ url: "https://forms.gle/XYZ123" }); // Replace with actual feedback form URL
}
