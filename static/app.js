const requestContainer = document.getElementById("requests");
const detailContainer = document.getElementById("details");
const statusText = document.getElementById("status");
const refreshButton = document.getElementById("refresh");
const clearButton = document.getElementById("clear");
const countText = document.getElementById("count");
const searchInput = document.getElementById("search");
const methodFilter = document.getElementById("methodFilter");
const statusFilter = document.getElementById("statusFilter");

let activeId = null;
let allRequests = [];
let eventSource = null;
let pollTimer = null;

const setStatus = (value) => {
  statusText.textContent = value;
};

const formatBadge = (status) => {
  if (status == null) {
    return "<span class=\"badge\">pending</span>";
  }
  const success = status >= 200 && status < 400;
  const label = `status ${status}`;
  return `<span class=\"badge ${success ? "success" : "error"}\">${label}</span>`;
};

const formatBody = (body) => {
  if (!body) {
    return "(empty)";
  }
  if (body.text !== undefined) {
    const trimmed = body.text.trim();
    if (trimmed) {
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch (error) {
        return body.text;
      }
    }
    return body.text;
  }
  if (body.base64) {
    return `[base64]\n${body.base64}`;
  }
  return JSON.stringify(body, null, 2);
};

const filterRequests = (requests) => {
  const searchValue = (searchInput.value || "").toLowerCase();
  const methodValue = methodFilter.value;
  const statusValue = statusFilter.value;
  return requests.filter((request) => {
    if (methodValue && request.method !== methodValue) {
      return false;
    }
    if (statusValue) {
      if (statusValue === "error") {
        if (!request.error) {
          return false;
        }
      } else if (request.status == null) {
        return false;
      } else {
        const prefix = Math.floor(request.status / 100);
        if (`${prefix}xx` !== statusValue) {
          return false;
        }
      }
    }
    if (searchValue) {
      const haystack = `${request.path} ${request.error ?? ""}`.toLowerCase();
      if (!haystack.includes(searchValue)) {
        return false;
      }
    }
    return true;
  });
};

const renderCount = (value) => {
  countText.textContent = value.toString();
};

const renderList = (requests) => {
  requestContainer.innerHTML = "";
  renderCount(requests.length);
  if (!requests.length) {
    requestContainer.textContent = "No requests captured yet.";
    return;
  }
  requests
    .slice()
    .reverse()
    .forEach((request) => {
      const card = document.createElement("div");
      card.className = "request-card";
      if (request.id === activeId) {
        card.classList.add("active");
      }
      card.innerHTML = `
        <div class="request-title">${request.method} ${request.path}</div>
        <div class="request-row">
          <span>${request.time}</span>
          ${formatBadge(request.status)}
        </div>
        <div class="request-row">
          <span>${request.duration_ms ?? "-"} ms</span>
          <span>${request.error ?? ""}</span>
        </div>
      `;
      card.addEventListener("click", () => {
        activeId = request.id;
        renderList(requests);
        fetchDetail(request.id);
      });
      requestContainer.appendChild(card);
    });
};

const renderDetail = (record) => {
  if (!record) {
    detailContainer.textContent = "Select a request to inspect.";
    return;
  }
  const requestHeaders = JSON.stringify(record.request_headers, null, 2);
  const responseHeaders = JSON.stringify(record.response_headers || {}, null, 2);
  detailContainer.innerHTML = `
    <div class="request-row">
      <strong>${record.method} ${record.path}</strong>
      ${formatBadge(record.status)}
    </div>
    <div class="request-row">
      <span>${record.time}</span>
      <span>${record.duration_ms ?? "-"} ms</span>
    </div>
    ${record.error ? `<p><strong>Error:</strong> ${record.error}</p>` : ""}
    <h3>Request Headers</h3>
    <pre>${requestHeaders}</pre>
    <h3>Request Body</h3>
    <pre>${formatBody(record.request_body)}</pre>
    <h3>Response Headers</h3>
    <pre>${responseHeaders}</pre>
    <h3>Response Body</h3>
    <pre>${formatBody(record.response_body)}</pre>
  `;
};

const fetchList = async () => {
  setStatus("Loading...");
  try {
    const response = await fetch("/api/requests");
    const payload = await response.json();
    allRequests = payload.requests || [];
    const filtered = filterRequests(allRequests);
    renderList(filtered);
    setStatus("Updated");
  } catch (error) {
    setStatus("Failed to load");
    requestContainer.textContent = "Failed to load requests.";
  }
};

const fetchDetail = async (id) => {
  setStatus("Loading detail...");
  try {
    const response = await fetch(`/api/requests/${id}`);
    const payload = await response.json();
    renderDetail(payload);
    setStatus("Updated");
  } catch (error) {
    detailContainer.textContent = "Failed to load request detail.";
    setStatus("Failed to load");
  }
};

const updateList = () => {
  const filtered = filterRequests(allRequests);
  renderList(filtered);
};

const startPolling = () => {
  if (pollTimer) {
    return;
  }
  pollTimer = setInterval(fetchList, 5000);
};

const startEvents = () => {
  if (eventSource) {
    return;
  }
  eventSource = new EventSource("/api/events");
  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "clear") {
        allRequests = [];
        activeId = null;
        renderDetail(null);
        updateList();
        return;
      }
      if (payload.type === "add" && payload.record) {
        allRequests.push(payload.record);
        updateList();
      }
      setStatus("Live");
    } catch (error) {
      setStatus("Live (parse error)");
    }
  };
  eventSource.onerror = () => {
    setStatus("Live connection lost, polling...");
    eventSource.close();
    eventSource = null;
    startPolling();
  };
};

refreshButton.addEventListener("click", () => {
  fetchList();
});

clearButton.addEventListener("click", async () => {
  try {
    await fetch("/api/requests", { method: "DELETE" });
    allRequests = [];
    activeId = null;
    renderDetail(null);
    updateList();
  } catch (error) {
    setStatus("Failed to clear");
  }
});

searchInput.addEventListener("input", () => updateList());
methodFilter.addEventListener("change", () => updateList());
statusFilter.addEventListener("change", () => updateList());

fetchList();
startEvents();
