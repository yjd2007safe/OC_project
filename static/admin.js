const messageEl = document.getElementById("admin-message");
const tableBody = document.getElementById("user-table-body");
const userSearch = document.getElementById("user-search");
const adminWelcome = document.getElementById("admin-welcome");

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
    throw new Error(data.message || "请求失败");
  }
  return data;
};

const setMessage = (text, isError = false) => {
  messageEl.textContent = text;
  messageEl.classList.toggle("error", isError);
};

const state = { users: [] };

const renderStats = (stats) => {
  document.getElementById("stat-total-users").textContent = stats.total_users;
  document.getElementById("stat-total-events").textContent = stats.total_events;
  document.getElementById("stat-today-users").textContent = stats.today_new_users;
  document.getElementById("stat-today-events").textContent = stats.today_new_events;
  document.getElementById("stat-system-status").textContent = stats.system_status;
};

const filteredUsers = () => {
  const keyword = userSearch.value.trim().toLowerCase();
  if (!keyword) {
    return state.users;
  }
  return state.users.filter((user) => user.username.toLowerCase().includes(keyword));
};

const refreshUsers = async () => {
  const data = await request("/api/admin/users");
  state.users = data.items || [];
  renderUsers();
};

const renderUsers = () => {
  tableBody.innerHTML = "";
  const users = filteredUsers();
  if (users.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = "<td colspan='6'>暂无用户</td>";
    tableBody.appendChild(row);
    return;
  }

  users.forEach((user) => {
    const row = document.createElement("tr");
    const statusText = user.enabled ? "启用" : "禁用";
    const roleText = user.is_admin ? "管理员" : "普通用户";
    row.innerHTML = `
      <td>${user.username}</td>
      <td>${roleText}</td>
      <td>${statusText}</td>
      <td>${user.event_count}</td>
      <td>${user.created_at || "-"}</td>
      <td class="admin-actions"></td>
    `;

    const actionsCell = row.querySelector(".admin-actions");

    const resetBtn = document.createElement("button");
    resetBtn.className = "secondary";
    resetBtn.textContent = "重置密码";
    resetBtn.addEventListener("click", async () => {
      const newPassword = prompt(`请输入 ${user.username} 的新密码（至少8位且包含字母和数字）`);
      if (!newPassword) {
        return;
      }
      if (!confirm(`确认重置 ${user.username} 的密码？`)) {
        return;
      }
      try {
        await request(`/api/admin/users/${user.username}/reset-password`, {
          method: "POST",
          body: JSON.stringify({ new_password: newPassword }),
        });
        setMessage(`${user.username} 密码已重置`);
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    const toggleBtn = document.createElement("button");
    toggleBtn.className = "secondary";
    toggleBtn.textContent = user.enabled ? "禁用" : "启用";
    toggleBtn.addEventListener("click", async () => {
      if (!confirm(`确认${user.enabled ? "禁用" : "启用"}用户 ${user.username}？`)) {
        return;
      }
      try {
        await request(`/api/admin/users/${user.username}/toggle`, { method: "POST" });
        await refreshUsers();
        setMessage(`${user.username} 状态已更新`);
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "删除";
    deleteBtn.addEventListener("click", async () => {
      if (!confirm(`删除用户 ${user.username} 后其日程将一并删除，确认继续？`)) {
        return;
      }
      try {
        await request(`/api/admin/users/${user.username}`, { method: "DELETE" });
        await refreshUsers();
        await loadStats();
        setMessage(`${user.username} 已删除`);
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    actionsCell.append(resetBtn, toggleBtn, deleteBtn);
    tableBody.appendChild(row);
  });
};

const loadStats = async () => {
  const stats = await request("/api/admin/stats");
  renderStats(stats);
};

const initialize = async () => {
  try {
    const session = await request("/session");
    if (!session.username || !session.is_admin) {
      window.location.href = "/";
      return;
    }
    adminWelcome.textContent = `欢迎，${session.username}`;
    await loadStats();
    await refreshUsers();
  } catch (error) {
    setMessage(error.message, true);
  }
};

document.getElementById("refresh-stats").addEventListener("click", async () => {
  await loadStats();
  await refreshUsers();
  setMessage("数据已刷新");
});

document.getElementById("back-home").addEventListener("click", () => {
  window.location.href = "/";
});

document.getElementById("admin-logout").addEventListener("click", async () => {
  await request("/logout", { method: "POST" });
  window.location.href = "/";
});

userSearch.addEventListener("input", renderUsers);

initialize();
