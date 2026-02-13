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
const dayViewButton = document.getElementById("view-day");
const weekViewButton = document.getElementById("view-week");
const monthViewButton = document.getElementById("view-month");
const previousRangeButton = document.getElementById("previous-range");
const nextRangeButton = document.getElementById("next-range");
const todayRangeButton = document.getElementById("today-range");
const calendarRangeLabel = document.getElementById("calendar-range-label");
const VIEW_MODE_STORAGE_KEY = "calendar-secretary-view-mode";
const AVAILABLE_VIEW_MODES = new Set(["day", "week", "month"]);

function getInitialViewMode() {
  const storedMode = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
  if (storedMode && AVAILABLE_VIEW_MODES.has(storedMode)) {
    return storedMode;
  }
  return "week";
}

const state = {
  schedules: [],
  editingId: null,
  viewMode: getInitialViewMode(),
  currentDate: normalizeDate(new Date()),
};

function normalizeDate(date) {
  const normalized = new Date(date);
  normalized.setHours(0, 0, 0, 0);
  return normalized;
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

function parseEventStart(item) {
  return new Date(item.time);
}

function parseEventEnd(item) {
  if (item.end_time) {
    return new Date(item.end_time);
  }
  return new Date(item.time);
}

function formatDateKey(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatRangeDate(date) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  }).format(date);
}

function getWeekStart(date) {
  const current = normalizeDate(date);
  const day = current.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  current.setDate(current.getDate() + diff);
  return current;
}

function getWeekDates(date) {
  const start = getWeekStart(date);
  return Array.from({ length: 7 }, (_, index) => {
    const target = new Date(start);
    target.setDate(start.getDate() + index);
    return target;
  });
}

function compareByTime(a, b) {
  return parseEventStart(a) - parseEventStart(b);
}

function getEventsForDate(date) {
  const dateKey = formatDateKey(date);
  return state.schedules
    .filter((item) => formatDateKey(parseEventStart(item)) === dateKey)
    .sort(compareByTime);
}

function getEventsForCurrentRange() {
  const current = state.currentDate;
  const year = current.getFullYear();
  const month = current.getMonth();
  const dateKey = formatDateKey(current);

  if (state.viewMode === "day") {
    return state.schedules
      .filter((item) => formatDateKey(parseEventStart(item)) === dateKey)
      .sort(compareByTime);
  }

  if (state.viewMode === "week") {
    const weekDates = getWeekDates(current).map((date) => formatDateKey(date));
    const weekSet = new Set(weekDates);
    return state.schedules
      .filter((item) => weekSet.has(formatDateKey(parseEventStart(item))))
      .sort(compareByTime);
  }

  return state.schedules
    .filter((item) => {
      const eventDate = parseEventStart(item);
      return eventDate.getFullYear() === year && eventDate.getMonth() === month;
    })
    .sort(compareByTime);
}

function renderCalendarRangeLabel() {
  const current = state.currentDate;
  if (state.viewMode === "day") {
    calendarRangeLabel.textContent = `日视图：${new Intl.DateTimeFormat("zh-CN", { dateStyle: "full" }).format(current)}`;
    return;
  }

  if (state.viewMode === "week") {
    const weekDates = getWeekDates(current);
    const first = weekDates[0];
    const last = weekDates[6];
    calendarRangeLabel.textContent = `周视图：${formatRangeDate(first)} - ${formatRangeDate(last)}`;
    return;
  }

  calendarRangeLabel.textContent = `月视图：${current.getFullYear()}年${`${current.getMonth() + 1}`.padStart(2, "0")}月`;
}

function renderEventSummary(item) {
  const wrapper = document.createElement("div");
  wrapper.className = "week-event-summary";

  const start = parseEventStart(item);
  const end = parseEventEnd(item);
  const time = document.createElement("p");
  time.className = "week-event-time";
  time.textContent = `${`${start.getHours()}`.padStart(2, "0")}:${`${start.getMinutes()}`.padStart(2, "0")} - ${`${end.getHours()}`.padStart(2, "0")}:${`${end.getMinutes()}`.padStart(2, "0")}`;

  const title = document.createElement("p");
  title.className = "week-event-title";
  title.textContent = item.title;

  const location = document.createElement("p");
  location.className = "week-event-location";
  location.textContent = item.location || "未设置地点";

  wrapper.append(time, title, location);
  return wrapper;
}

function renderWeekView() {
  const weekDates = getWeekDates(state.currentDate);
  const weekView = document.createElement("div");
  weekView.className = "week-view";

  const weekHeader = document.createElement("div");
  weekHeader.className = "week-grid week-grid-header";

  const weekBody = document.createElement("div");
  weekBody.className = "week-grid week-grid-body";

  weekDates.forEach((date) => {
    const headerCell = document.createElement("div");
    headerCell.className = "week-day-header-cell";
    headerCell.textContent = formatRangeDate(date);
    weekHeader.appendChild(headerCell);

    const dayCard = document.createElement("li");
    dayCard.className = "week-day-card";

    const events = getEventsForDate(date);
    const eventContainer = document.createElement("div");
    eventContainer.className = "week-day-events";

    if (events.length === 0) {
      const empty = document.createElement("p");
      empty.className = "week-day-empty";
      empty.textContent = "无日程";
      eventContainer.appendChild(empty);
    } else {
      events.forEach((item) => {
        eventContainer.appendChild(renderEventSummary(item));
      });
    }

    dayCard.appendChild(eventContainer);
    weekBody.appendChild(dayCard);
  });

  weekView.append(weekHeader, weekBody);
  scheduleList.appendChild(weekView);
}

function getMonthDates(date) {
  const current = normalizeDate(date);
  const monthStart = new Date(current.getFullYear(), current.getMonth(), 1);
  const monthEnd = new Date(current.getFullYear(), current.getMonth() + 1, 0);
  const calendarStart = getWeekStart(monthStart);
  const calendarEnd = getWeekStart(monthEnd);
  calendarEnd.setDate(calendarEnd.getDate() + 6);

  const dates = [];
  const pointer = new Date(calendarStart);
  while (pointer <= calendarEnd) {
    dates.push(new Date(pointer));
    pointer.setDate(pointer.getDate() + 1);
  }
  return dates;
}

function renderMonthDaySummary(events) {
  const summary = document.createElement("div");
  summary.className = "month-day-summary";

  if (events.length === 0) {
    const empty = document.createElement("p");
    empty.className = "month-day-empty";
    empty.textContent = "无日程";
    summary.appendChild(empty);
    return summary;
  }

  const count = document.createElement("p");
  count.className = "month-day-count";
  count.textContent = `共 ${events.length} 项`;
  summary.appendChild(count);

  events.slice(0, 2).forEach((item) => {
    const start = parseEventStart(item);
    const event = document.createElement("p");
    event.className = "month-day-item";
    event.textContent = `${`${start.getHours()}`.padStart(2, "0")}:${`${start.getMinutes()}`.padStart(2, "0")} ${item.title}`;
    summary.appendChild(event);
  });

  if (events.length > 2) {
    const more = document.createElement("p");
    more.className = "month-day-more";
    more.textContent = `+${events.length - 2} 项`;
    summary.appendChild(more);
  }

  return summary;
}

function renderMonthView() {
  const current = state.currentDate;
  const monthDates = getMonthDates(current);
  const monthView = document.createElement("div");
  monthView.className = "month-view";

  const weekdayLabels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  const monthHeader = document.createElement("div");
  monthHeader.className = "month-grid month-grid-header";
  weekdayLabels.forEach((label) => {
    const cell = document.createElement("div");
    cell.className = "month-header-cell";
    cell.textContent = label;
    monthHeader.appendChild(cell);
  });

  const monthBody = document.createElement("div");
  monthBody.className = "month-grid month-grid-body";

  monthDates.forEach((date) => {
    const dayCell = document.createElement("div");
    dayCell.className = "month-day-cell";

    if (date.getMonth() !== current.getMonth()) {
      dayCell.classList.add("outside-month");
    }

    if (formatDateKey(date) === formatDateKey(new Date())) {
      dayCell.classList.add("is-today");
    }

    const dayNumber = document.createElement("p");
    dayNumber.className = "month-day-number";
    dayNumber.textContent = `${date.getDate()}`;

    dayCell.append(dayNumber, renderMonthDaySummary(getEventsForDate(date)));
    monthBody.appendChild(dayCell);
  });

  monthView.append(monthHeader, monthBody);
  scheduleList.appendChild(monthView);
}

function renderListView(items) {
  if (items.length === 0) {
    const empty = document.createElement("li");
    empty.className = "schedule-item";
    empty.textContent = "当前视图暂无日程，请在左侧新增。";
    scheduleList.appendChild(empty);
    return;
  }

  items.forEach((item) => {
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
}

const renderSchedules = () => {
  scheduleList.innerHTML = "";
  renderCalendarRangeLabel();

  if (state.viewMode === "week") {
    renderWeekView();
    return;
  }

  if (state.viewMode === "month") {
    renderMonthView();
    return;
  }

  const items = getEventsForCurrentRange();
  renderListView(items);
};

function updateViewButtons() {
  dayViewButton.classList.toggle("active", state.viewMode === "day");
  weekViewButton.classList.toggle("active", state.viewMode === "week");
  monthViewButton.classList.toggle("active", state.viewMode === "month");
}

function switchView(viewMode) {
  state.viewMode = viewMode;
  window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
  updateViewButtons();
  renderSchedules();
}

function moveRange(direction) {
  if (state.viewMode === "day") {
    state.currentDate.setDate(state.currentDate.getDate() + direction);
  } else if (state.viewMode === "week") {
    state.currentDate.setDate(state.currentDate.getDate() + 7 * direction);
  } else {
    state.currentDate.setMonth(state.currentDate.getMonth() + direction);
  }
  state.currentDate = normalizeDate(state.currentDate);
  renderSchedules();
}

const loadSchedules = async () => {
  const data = await request("/api/events");
  state.schedules = data.items || [];
  renderSchedules();
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

dayViewButton.addEventListener("click", () => switchView("day"));
weekViewButton.addEventListener("click", () => switchView("week"));
monthViewButton.addEventListener("click", () => switchView("month"));
previousRangeButton.addEventListener("click", () => moveRange(-1));
nextRangeButton.addEventListener("click", () => moveRange(1));
todayRangeButton.addEventListener("click", () => {
  state.currentDate = normalizeDate(new Date());
  renderSchedules();
});

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
  updateViewButtons();
  renderCalendarRangeLabel();
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
