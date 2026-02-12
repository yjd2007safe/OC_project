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
const calendarContent = document.getElementById("calendar-content");
const viewTitle = document.getElementById("view-title");
const viewButtons = Array.from(document.querySelectorAll(".view-button"));
const prevPeriodButton = document.getElementById("prev-period");
const nextPeriodButton = document.getElementById("next-period");
const todayPeriodButton = document.getElementById("today-period");

const VIEW_STORAGE_KEY = "calendarSecretary.view";

const state = {
  schedules: [],
  editingId: null,
  currentDate: new Date(),
  currentView: localStorage.getItem(VIEW_STORAGE_KEY) || "day",
};

if (!["day", "week", "month"].includes(state.currentView)) {
  state.currentView = "day";
}

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
  renderCurrentView();
};

const toDate = (dateString) => {
  if (!dateString) {
    return null;
  }
  const parsed = new Date(dateString);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const dayStart = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate());

const isSameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

const startOfWeek = (value) => {
  const start = dayStart(value);
  const day = start.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  start.setDate(start.getDate() + diff);
  return start;
};

const endOfWeek = (value) => {
  const end = startOfWeek(value);
  end.setDate(end.getDate() + 6);
  return end;
};

const formatDate = (value) =>
  value.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" });

const formatMonthTitle = (value) => `${value.getFullYear()}年${value.getMonth() + 1}月`;

const getSchedulesForDate = (targetDate) =>
  state.schedules
    .filter((item) => {
      const eventDate = toDate(item.time);
      return eventDate && isSameDay(eventDate, targetDate);
    })
    .sort((a, b) => a.time.localeCompare(b.time));

const createScheduleListItem = (item) => {
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

  return li;
};

const renderDayView = () => {
  const items = getSchedulesForDate(state.currentDate);
  viewTitle.textContent = `日视图 · ${formatDate(state.currentDate)}`;

  scheduleList.innerHTML = "";
  scheduleList.classList.remove("hidden");
  calendarContent.innerHTML = "";

  if (items.length === 0) {
    const empty = document.createElement("li");
    empty.className = "schedule-item";
    empty.textContent = "当天暂无日程。";
    scheduleList.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    scheduleList.appendChild(createScheduleListItem(item));
  });
};

const renderWeekView = () => {
  const start = startOfWeek(state.currentDate);
  const end = endOfWeek(state.currentDate);
  viewTitle.textContent = `周视图 · ${formatDate(start)} - ${formatDate(end)}`;

  scheduleList.classList.add("hidden");
  calendarContent.innerHTML = "";

  const weekWrap = document.createElement("div");
  weekWrap.className = "week-view";

  for (let i = 0; i < 7; i += 1) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    const dayItems = getSchedulesForDate(day);

    const dayCol = document.createElement("section");
    dayCol.className = "week-day";

    const dayTitle = document.createElement("h4");
    dayTitle.textContent = formatDate(day);

    const list = document.createElement("ul");
    list.className = "week-events";
    if (dayItems.length === 0) {
      const empty = document.createElement("li");
      empty.className = "empty-note";
      empty.textContent = "暂无";
      list.appendChild(empty);
    } else {
      dayItems.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.time.slice(11, 16)} ${item.title}`;
        list.appendChild(li);
      });
    }

    dayCol.append(dayTitle, list);
    weekWrap.appendChild(dayCol);
  }

  calendarContent.appendChild(weekWrap);
};

const renderMonthView = () => {
  const current = new Date(state.currentDate.getFullYear(), state.currentDate.getMonth(), 1);
  viewTitle.textContent = `月视图 · ${formatMonthTitle(current)}`;

  scheduleList.classList.add("hidden");
  calendarContent.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "month-grid";

  ["周一", "周二", "周三", "周四", "周五", "周六", "周日"].forEach((label) => {
    const header = document.createElement("div");
    header.className = "month-cell month-header";
    header.textContent = label;
    grid.appendChild(header);
  });

  const start = startOfWeek(current);
  const month = current.getMonth();

  for (let i = 0; i < 42; i += 1) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    const items = getSchedulesForDate(day);

    const cell = document.createElement("div");
    cell.className = "month-cell";
    if (day.getMonth() !== month) {
      cell.classList.add("outside");
    }
    if (isSameDay(day, new Date())) {
      cell.classList.add("today");
    }

    const dayLabel = document.createElement("div");
    dayLabel.className = "month-day";
    dayLabel.textContent = String(day.getDate());

    const summary = document.createElement("div");
    summary.className = "month-summary";
    if (items.length === 0) {
      summary.textContent = "无日程";
    } else if (items.length === 1) {
      summary.textContent = items[0].title;
    } else {
      summary.textContent = `${items.length} 个日程`;
    }

    cell.append(dayLabel, summary);
    grid.appendChild(cell);
  }

  calendarContent.appendChild(grid);
};

const renderCurrentView = () => {
  viewButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.currentView);
  });

  if (state.currentView === "week") {
    renderWeekView();
    return;
  }

  if (state.currentView === "month") {
    renderMonthView();
    return;
  }

  renderDayView();
};

const shiftPeriod = (direction) => {
  if (state.currentView === "month") {
    state.currentDate.setMonth(state.currentDate.getMonth() + direction);
  } else if (state.currentView === "week") {
    state.currentDate.setDate(state.currentDate.getDate() + (direction * 7));
  } else {
    state.currentDate.setDate(state.currentDate.getDate() + direction);
  }
  renderCurrentView();
};

const deleteSchedule = async (id) => {
  try {
    await request(`/api/events/${id}`, { method: "DELETE" });
    state.schedules = state.schedules.filter((item) => item.id !== id);
    renderCurrentView();
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
    renderCurrentView();
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

viewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.currentView = button.dataset.view;
    localStorage.setItem(VIEW_STORAGE_KEY, state.currentView);
    renderCurrentView();
  });
});

prevPeriodButton.addEventListener("click", () => shiftPeriod(-1));
nextPeriodButton.addEventListener("click", () => shiftPeriod(1));
todayPeriodButton.addEventListener("click", () => {
  state.currentDate = new Date();
  renderCurrentView();
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
  renderCurrentView();
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
