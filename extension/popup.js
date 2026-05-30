const DEFAULT_USER_ID = "11111111-1111-4111-8111-111111111111";
const DEFAULT_API_URL = "http://127.0.0.1:8000";

const apiUrlInput = document.querySelector("#apiUrl");
const userIdInput = document.querySelector("#userId");
const payloadInput = document.querySelector("#payload");
const statusEl = document.querySelector("#status");
const detectedEl = document.querySelector("#detected");
const balanceOverrideInput = document.querySelector("#balanceOverride");
const captureButton = document.querySelector("#captureButton");
const sendButton = document.querySelector("#sendButton");
const applyOverrideButton = document.querySelector("#applyOverrideButton");

loadSettings();

captureButton.addEventListener("click", captureCurrentTab);
sendButton.addEventListener("click", sendPayload);
applyOverrideButton.addEventListener("click", applyBalanceCorrection);
apiUrlInput.addEventListener("change", saveSettings);
userIdInput.addEventListener("change", saveSettings);

async function loadSettings() {
  const saved = await chrome.storage.local.get(["apiUrl", "userId"]);
  apiUrlInput.value = saved.apiUrl || DEFAULT_API_URL;
  userIdInput.value = saved.userId || DEFAULT_USER_ID;
}

async function saveSettings() {
  await chrome.storage.local.set({
    apiUrl: apiUrlInput.value.trim() || DEFAULT_API_URL,
    userId: userIdInput.value.trim() || DEFAULT_USER_ID,
  });
}

async function captureCurrentTab() {
  setStatus("Capturing...");
  captureButton.disabled = true;

  try {
    await saveSettings();
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) {
      throw new Error("No active tab found.");
    }

    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractVisiblePage,
    });

    const payload = LoyaltyParser.normalizeSnapshot(result, userIdInput.value.trim() || DEFAULT_USER_ID);
    const safety = LoyaltyParser.inspectPayloadSafety(payload);
    payload.metadata.safety_findings = safety.findings;
    payloadInput.value = JSON.stringify(payload, null, 2);
    detectedEl.textContent = LoyaltyParser.summarizePayload(payload);
    setStatus(safety.ok ? "Captured" : "Review required");
  } catch (error) {
    setStatus(error.message || "Capture failed");
  } finally {
    captureButton.disabled = false;
  }
}

async function sendPayload() {
  setStatus("Sending...");
  sendButton.disabled = true;

  try {
    await saveSettings();
    const payload = JSON.parse(payloadInput.value);
    const safety = LoyaltyParser.inspectPayloadSafety(payload);
    if (!safety.ok) {
      throw new Error(`Blocked: ${safety.findings.join(", ")}`);
    }

    const response = await fetch(`${apiUrlInput.value.replace(/\/$/, "")}/ingestion/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`API ${response.status}: ${text}`);
    }

    const result = await response.json();
    detectedEl.textContent = `${result.run.account_count} accounts, ${result.run.offer_count} offers`;
    setStatus(`Sent: ${result.run.status}`);
  } catch (error) {
    setStatus(error.message || "Send failed");
  } finally {
    sendButton.disabled = false;
  }
}

function applyBalanceCorrection() {
  try {
    const balance = Number.parseInt(balanceOverrideInput.value.replaceAll(",", ""), 10);
    if (!Number.isFinite(balance) || balance < 0) {
      throw new Error("Enter a valid points balance.");
    }

    const payload = JSON.parse(payloadInput.value);
    if (!payload.accounts?.length) {
      throw new Error("No account in payload to correct.");
    }

    payload.accounts[0].points_balance = balance;
    payload.metadata = {
      ...(payload.metadata || {}),
      manual_balance_override: true,
    };
    payloadInput.value = JSON.stringify(payload, null, 2);
    detectedEl.textContent = LoyaltyParser.summarizePayload(payload);
    setStatus("Correction applied");
  } catch (error) {
    setStatus(error.message || "Correction failed");
  }
}

function setStatus(message) {
  statusEl.textContent = message;
}

function extractVisiblePage() {
  const text = document.body?.innerText || "";
  return {
    url: location.href,
    title: document.title,
    text: text.slice(0, 120000),
    captured_at: new Date().toISOString(),
  };
}
