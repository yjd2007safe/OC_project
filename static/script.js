const loginSection = document.getElementById("login-section");
const appSection = document.getElementById("app-section");
const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");
const scheduleForm = document.getElementById("schedule-form");
const scheduleList = document.getElementById("schedule-list");
const resetButton = document.getElementById("reset-button");
const formMessage = document.getElementById("form-message");
const welcome = document.getElementById("welcome");
const logoutButton = document.getElementById("logout-button");
const formTitle = document.getElementById("form-title");

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
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.message || "请求失败";
    throw new Error(message);
  }
  return data;
};

const setMessage = (element, message, isError = false) => {
  element.textContent = message;
  element.classList.toggle("error", isError);
};

const setEditing = (item = null) => {
  state.editingId = item ? item.id : null;
  scheduleForm.id.value = item ? item.id : "";
  scheduleForm.title.value = item ? item.title : "";
  scheduleForm.time.value = item ? item.time : "";
  scheduleForm.location.value = item ? item.location : "";
  scheduleForm.description.value = item ? item.description : "";
  formTitle.textContent = item ? "编辑日程" : "新增日程";
};

const loadSchedules = async () => {
  const data = await request("/api/schedules");
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
    time.innerHTML = `<strong>时间：</strong>${item.time}`;

    const location = document.createElement("p");
    location.innerHTML = `<strong>地点：</strong>${item.location}`;

    const description = document.createElement("p");
    description.innerHTML = `<strong>描述：</strong>${item.description}`;

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

    li.append(title, time, location, description, meta, actions);
    scheduleList.appendChild(li);
  });
};

const deleteSchedule = async (id) => {
  try {
    await request(`/api/schedules/${id}`, { method: "DELETE" });
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
    loginForm.reset();
    await loadSchedules();
  } catch (error) {
    setMessage(loginMessage, error.message, true);
  }
});

scheduleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(formMessage, "");
  const payload = {
    title: scheduleForm.title.value.trim(),
    time: scheduleForm.time.value,
    location: scheduleForm.location.value.trim(),
    description: scheduleForm.description.value.trim(),
  };

  try {
    if (state.editingId) {
      const updated = await request(`/api/schedules/${state.editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      state.schedules = state.schedules.map((item) =>
        item.id === updated.id ? updated : item,
      );
      setMessage(formMessage, "日程已更新。", false);
    } else {
      const created = await request("/api/schedules", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.schedules.push(created);
      setMessage(formMessage, "日程已创建。", false);
    }
    setEditing();
    renderSchedules();
  } catch (error) {
    setMessage(formMessage, error.message, true);
  }
});

resetButton.addEventListener("click", () => {
  setEditing();
  setMessage(formMessage, "");
});

logoutButton.addEventListener("click", async () => {
  await request("/logout", { method: "POST" });
  appSection.classList.add("hidden");
  loginSection.classList.remove("hidden");
  setEditing();
});

const initialize = async () => {
  try {
    const data = await request("/session");
    if (data.username) {
      loginSection.classList.add("hidden");
      appSection.classList.remove("hidden");
      welcome.textContent = `欢迎，${data.username}`;
      await loadSchedules();
    }
  } catch (error) {
    console.error(error);
  }
};

initialize();
