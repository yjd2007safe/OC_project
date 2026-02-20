const loginSection = document.getElementById("login-section");
const appSection = document.getElementById("app-section");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const loginMessage = document.getElementById("login-message");
const registerMessage = document.getElementById("register-message");
const scheduleForm = document.getElementById("schedule-form");
const scheduleList = document.getElementById("schedule-list");
const resetButton = document.getElementById("reset-button");
const formMessage = document.getElementById("form-message");
const welcome = document.getElementById("welcome");
const logoutButton = document.getElementById("logout-button");
const adminLink = document.getElementById("admin-link");
const formTitle = document.getElementById("form-title");
const recurrenceEndTypeWrap = document.getElementById("recurrence-end-type-wrap");
const recurrenceUntilWrap = document.getElementById("recurrence-until-wrap");
const recurrenceCountWrap = document.getElementById("recurrence-count-wrap");

const state = {
  schedules: [],
  editingId: null,
};

const request = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  let data = {};
  let rawText = "";

  if (contentType.includes("application/json")) {
    data = await response.json().catch(() => ({}));
  } else {
    rawText = await response.text().catch(() => "");
  }

  if (!response.ok) {
    const fallback = rawText ? `请求失败（${response.status}）` : "请求失败";
    const message = data.message || fallback;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
};

const setMessage = (element, message, isError = false) => {
  element.textContent = message;
  element.classList.toggle("error", isError);
};

const recurrenceText = (recurrence) => {
  if (!recurrence || recurrence.frequency === "none") {
    return "不重复";
  }
  const names = {
    daily: "每天",
    weekly: "每周",
    monthly: "每月",
    yearly: "每年",
  };
  if (recurrence.end_type === "until" && recurrence.until) {
    return `${names[recurrence.frequency]}，截止 ${recurrence.until}`;
  }
  if (recurrence.end_type === "count" && recurrence.count) {
    return `${names[recurrence.frequency]}，共 ${recurrence.count} 次`;
  }
  return `${names[recurrence.frequency]}，永不结束`;
};

const refreshRecurrenceFields = () => {
  const frequency = scheduleForm.recurrence_frequency.value;
  const endType = scheduleForm.recurrence_end_type.value;
  const showRecurrence = frequency !== "none";

  recurrenceEndTypeWrap.classList.toggle("hidden", !showRecurrence);
  recurrenceUntilWrap.classList.toggle("hidden", !showRecurrence || endType !== "until");
  recurrenceCountWrap.classList.toggle("hidden", !showRecurrence || endType !== "count");
};

const setEditing = (item = null) => {
  state.editingId = item ? item.id : null;
  scheduleForm.id.value = item ? item.id : "";
  scheduleForm.title.value = item ? item.title : "";
  scheduleForm.time.value = item ? item.time : "";
  scheduleForm.end_time.value = item ? item.end_time : "";
  scheduleForm.location.value = item ? item.location : "";
  scheduleForm.description.value = item ? item.description : "";

  const recurrence = item?.recurrence || { frequency: "none", end_type: "never", until: "", count: "" };
  scheduleForm.recurrence_frequency.value = recurrence.frequency || "none";
  scheduleForm.recurrence_end_type.value = recurrence.end_type || "never";
  scheduleForm.recurrence_until.value = recurrence.until || "";
  scheduleForm.recurrence_count.value = recurrence.count || "";

  formTitle.textContent = item ? "编辑日程" : "新增日程";
  refreshRecurrenceFields();
};

const buildRecurrencePayload = () => {
  const frequency = scheduleForm.recurrence_frequency.value;
  if (frequency === "none") {
    return { frequency: "none" };
  }

  const endType = scheduleForm.recurrence_end_type.value;
  const payload = {
    frequency,
    end_type: endType,
  };

  if (endType === "until") {
    payload.until = scheduleForm.recurrence_until.value;
  }
  if (endType === "count") {
    payload.count = Number.parseInt(scheduleForm.recurrence_count.value, 10);
  }

  return payload;
};

const loadSchedules = async () => {
  const data = await request("/api/events");
  state.schedules = data.items || [];
  renderSchedules();
};

const renderSchedules = () => {
  scheduleList.innerHTML = "";
  if (state.schedules.length === 0) {
    const empty = document.createElement("li");
    empty.className = "schedule-item";
    empty.textContent = "暂无日程，请在左侧新增。";
    scheduleList.appendChild(empty);
    return;
  }

  state.schedules.forEach((item) => {
    const li = document.createElement("li");
    li.className = "schedule-item";

    const title = document.createElement("h4");
    title.textContent = item.title;

    const time = document.createElement("p");
    time.innerHTML = `<strong>时间：</strong>${item.time} - ${item.end_time || ""}`;

    const location = document.createElement("p");
    location.innerHTML = `<strong>地点：</strong>${item.location}`;

    const description = document.createElement("p");
    description.innerHTML = `<strong>描述：</strong>${item.description}`;

    const recurrence = document.createElement("p");
    recurrence.innerHTML = `<strong>重复：</strong>${recurrenceText(item.recurrence)}`;

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `编号 #${item.id}`;

    const actions = document.createElement("div");
    actions.className = "item-actions";

    const editButton = document.createElement("button");
    editButton.className = "secondary";
    editButton.textContent = "编辑";
    editButton.addEventListener("click", () => setEditing(item));

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "删除";
    deleteButton.addEventListener("click", () => deleteSchedule(item.id));

    actions.append(editButton, deleteButton);

    li.append(title, time, location, description, recurrence, meta, actions);
    scheduleList.appendChild(li);
  });
};

const deleteSchedule = async (id) => {
  try {
    await request(`/api/events/${id}`, { method: "DELETE" });
    state.schedules = state.schedules.filter((item) => item.id !== id);
    renderSchedules();
    setMessage(formMessage, "日程已删除。", false);
  } catch (error) {
    setMessage(formMessage, error.message, true);
  }
};

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(loginMessage, "");
  const payload = {
    username: loginForm.username.value.trim(),
    password: loginForm.password.value,
  };
  try {
    const data = await request("/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    loginSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    welcome.textContent = `欢迎，${data.username}`;
    adminLink.classList.toggle("hidden", !data.is_admin);
    loginForm.reset();
    await loadSchedules();
  } catch (error) {
    setMessage(loginMessage, error.message, true);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(registerMessage, "");
  const payload = {
    username: registerForm.username.value.trim(),
    password: registerForm.password.value,
  };
  try {
    const data = await request("/api/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setMessage(registerMessage, `注册成功，API Key: ${data.api_key}`, false);
    registerForm.reset();
  } catch (error) {
    setMessage(registerMessage, error.message, true);
  }
});

scheduleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(formMessage, "");
  const payload = {
    title: scheduleForm.title.value.trim(),
    time: scheduleForm.time.value,
    end_time: scheduleForm.end_time.value,
    location: scheduleForm.location.value.trim(),
    description: scheduleForm.description.value.trim(),
    recurrence: buildRecurrencePayload(),
  };

  try {
    if (state.editingId) {
      const updated = await request(`/api/events/${state.editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      state.schedules = state.schedules.map((item) =>
        item.id === updated.id ? updated : item,
      );
      setMessage(formMessage, "日程已更新。", false);
    } else {
      const created = await request("/api/events", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.schedules.push(created);
      setMessage(formMessage, "日程已创建。", false);
    }
    setEditing();
    renderSchedules();
  } catch (error) {
    if (error.status === 409) {
      setMessage(formMessage, `⚠️ ${error.message}`, true);
      return;
    }
    setMessage(formMessage, error.message, true);
  }
});

scheduleForm.recurrence_frequency.addEventListener("change", refreshRecurrenceFields);
scheduleForm.recurrence_end_type.addEventListener("change", refreshRecurrenceFields);

resetButton.addEventListener("click", () => {
  setEditing();
  setMessage(formMessage, "");
});

logoutButton.addEventListener("click", async () => {
  await request("/logout", { method: "POST" });
  appSection.classList.add("hidden");
  loginSection.classList.remove("hidden");
  adminLink.classList.add("hidden");
  setEditing();
});

adminLink.addEventListener("click", () => {
  window.location.href = "/admin";
});

const initialize = async () => {
  setEditing();
  try {
    const data = await request("/session");
    if (data.username) {
      loginSection.classList.add("hidden");
      appSection.classList.remove("hidden");
      welcome.textContent = `欢迎，${data.username}`;
    adminLink.classList.toggle("hidden", !data.is_admin);
      await loadSchedules();
    }
  } catch (error) {
    console.error(error);
  }
};

initialize();
