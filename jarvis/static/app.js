const chat = document.querySelector("#chat");
const composer = document.querySelector("#composer");
const messageInput = document.querySelector("#message");
const statusBadge = document.querySelector("#status");

function addMessage(kind, text, toolResults = []) {
  const item = document.createElement("article");
  item.className = `message ${kind}`;
  item.textContent = text;
  if (toolResults.length > 0) {
    const tools = document.createElement("div");
    tools.className = "tools";
    tools.textContent = `Tools: ${toolResults.map((result) => result.name).join(", ")}`;
    item.appendChild(tools);
  }
  chat.appendChild(item);
  chat.scrollTop = chat.scrollHeight;
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  addMessage("user", message);
  messageInput.value = "";
  messageInput.disabled = true;
  composer.querySelector("button").disabled = true;
  statusBadge.textContent = "Thinking";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, session_id: "browser" }),
    });
    if (!response.ok) throw new Error(await response.text());
    const payload = await response.json();
    addMessage("jarvis", payload.answer || "(no answer)", payload.tool_results || []);
    statusBadge.textContent = "Local";
  } catch (error) {
    addMessage("jarvis", `Request failed: ${error.message}`);
    statusBadge.textContent = "Error";
  } finally {
    messageInput.disabled = false;
    composer.querySelector("button").disabled = false;
    messageInput.focus();
  }
});
