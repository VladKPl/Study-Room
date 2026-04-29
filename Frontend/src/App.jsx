import { useEffect, useState } from "react";
import "./App.css";
import AuthModal from "./components/AuthModal";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1/auth";
const VALID_ROLES = new Set(["guest", "student", "author", "admin"]);

function parseGoogleCallbackPayload() {
  const rawFragment = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(rawFragment);

  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  const userId = params.get("user_id");
  const email = params.get("email");
  const fullName = params.get("full_name");
  const role = params.get("role");
  const tokenType = params.get("token_type") ?? "bearer";

  if (!accessToken || !refreshToken || !userId || !email || !fullName || !role) {
    return {
      ok: false,
      error: "Не удалось завершить вход через Google. Попробуйте снова.",
    };
  }

  const normalizedRole = role.toLowerCase();
  if (!VALID_ROLES.has(normalizedRole)) {
    return {
      ok: false,
      error: "Получена неизвестная роль пользователя после входа через Google.",
    };
  }

  const parsedUserId = Number(userId);
  if (!Number.isFinite(parsedUserId) || parsedUserId <= 0) {
    return {
      ok: false,
      error: "Получен некорректный идентификатор пользователя.",
    };
  }

  return {
    ok: true,
    accessToken,
    refreshToken,
    tokenType,
    restoredUser: {
      id: parsedUserId,
      email,
      full_name: fullName,
      role: normalizedRole,
      is_active: true,
      is_email_verified: true,
    },
  };
}

function App() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isAuthorOfferOpen, setIsAuthorOfferOpen] = useState(false);
  const [authorOfferError, setAuthorOfferError] = useState("");
  const [pendingAuthorAfterRegister, setPendingAuthorAfterRegister] = useState(false);
  const [authMode, setAuthMode] = useState("login");

  const [currentUser, setCurrentUser] = useState(() => {
    const savedUser = localStorage.getItem("auth_user");

    if (!savedUser) {
      return null;
    }

    try {
      return JSON.parse(savedUser);
    } catch (error) {
      console.error("Не удалось прочитать auth_user из localStorage:", error);
      localStorage.removeItem("auth_user");
      return null;
    }
  });

  const platformMenuItems = [{ label: "О платформе", href: "#" }];
  const currentRole = currentUser?.role ?? "guest";
  const isGoogleCallbackPage = window.location.pathname === "/auth/google/callback";
  const googleCallbackResult = isGoogleCallbackPage ? parseGoogleCallbackPayload() : null;

  useEffect(() => {
    if (!isGoogleCallbackPage || !googleCallbackResult?.ok) {
      return;
    }

    localStorage.setItem("access_token", googleCallbackResult.accessToken);
    localStorage.setItem("refresh_token", googleCallbackResult.refreshToken);
    localStorage.setItem("token_type", googleCallbackResult.tokenType);
    localStorage.setItem("auth_user", JSON.stringify(googleCallbackResult.restoredUser));
    window.location.replace("/");
  }, [isGoogleCallbackPage, googleCallbackResult]);

  const continueAuthorFlowAfterAuth = (user) => {
    if (user.role === "author" || user.role === "admin") {
      setPendingAuthorAfterRegister(false);
      setIsAuthorOfferOpen(false);
      return;
    }

    if (!pendingAuthorAfterRegister) {
      return;
    }

    setPendingAuthorAfterRegister(false);
    setIsAuthorOfferOpen(true);
  };

  const handleLoginSubmit = async (formData) => {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: formData.email,
        password: formData.password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось выполнить вход.");
    }

    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));

    setCurrentUser(data.user);
    setIsAuthModalOpen(false);
    continueAuthorFlowAfterAuth(data.user);

    return {
      message: `Вы вошли как ${data.user.full_name}`,
    };
  };

  const handleRegisterSubmit = async (formData) => {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: formData.email,
        password: formData.password,
        full_name: formData.name,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось создать аккаунт.");
    }

    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));

    setCurrentUser(data.user);
    setIsAuthModalOpen(false);
    continueAuthorFlowAfterAuth(data.user);

    return {
      message: `Аккаунт создан: ${data.user.full_name}`,
    };
  };

  const handleGoogleAuth = async () => {
    window.location.href = `${API_BASE_URL}/google/login`;

    return {
      message: "Переходим к авторизации через Google.",
    };
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("auth_user");
    setCurrentUser(null);
  };

  const handleBecomeAuthorClick = () => {
    setAuthorOfferError("");
    if (currentRole === "guest") {
      setPendingAuthorAfterRegister(true);
      setAuthMode("register");
      setIsAuthModalOpen(true);
      return;
    }

    if (currentRole === "author" || currentRole === "admin") {
      window.alert("Раздел «Мои курсы» пока в разработке.");
      return;
    }

    setIsAuthorOfferOpen(true);
  };

  const handleConfirmBecomeAuthor = async () => {
    if (!currentUser || currentRole !== "student") {
      return;
    }

    const accessToken = localStorage.getItem("access_token");
    if (!accessToken) {
      setIsAuthorOfferOpen(false);
      setAuthorOfferError("");
      setAuthMode("login");
      setIsAuthModalOpen(true);
      return;
    }

    const response = await fetch(`${API_BASE_URL}/become-author`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Не удалось обновить роль до автора.");
    }

    localStorage.setItem("auth_user", JSON.stringify(data.user));
    setCurrentUser(data.user);
    setAuthorOfferError("");
    setIsAuthorOfferOpen(false);
    window.alert("Роль автора активирована. Раздел «Мои курсы» пока в разработке.");
  };

  const handleConfirmBecomeAuthorClick = async () => {
    try {
      await handleConfirmBecomeAuthor();
    } catch (error) {
      setAuthorOfferError(error?.message ?? "Не удалось отправить запрос на получение роли автора.");
    }
  };

  const handleAuthModalClose = () => {
    setIsAuthModalOpen(false);
    setPendingAuthorAfterRegister(false);
  };

  if (isGoogleCallbackPage) {
    const hasCallbackError = !googleCallbackResult?.ok;
    const callbackErrorMessage = hasCallbackError
      ? googleCallbackResult?.error ?? "Не удалось завершить вход через Google."
      : "";

    return (
      <div className="page">
        <main className="page-content page-content--centered">
          <section className="hero hero--landing">
            <h1 className="hero__title hero__title--centered">
              {hasCallbackError ? "Ошибка входа через Google" : "Завершаем вход..."}
            </h1>
            <p className="hero__text hero__text--centered">
              {hasCallbackError
                ? callbackErrorMessage
                : "Пожалуйста, подождите. Вы будете перенаправлены автоматически."}
            </p>
            {hasCallbackError ? (
              <div className="hero__actions hero__actions--centered">
                <button
                  type="button"
                  className="create-course-button"
                  onClick={() => window.location.replace("/")}
                >
                  Вернуться на главную
                </button>
              </div>
            ) : null}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="site-header">
        <div className="site-header__inner">
          <div className="site-header__left">
            <button className="logo" type="button">
              StudyRoom
            </button>

            <nav className="nav">
              <div className="nav-item">
                <button type="button" className="nav-button">
                  <span>Платформа</span>
                  <span className="nav-button__arrow" aria-hidden="true"></span>
                </button>

                <div className="dropdown">
                  {platformMenuItems.map((item) => (
                    <a key={item.label} className="dropdown__item" href={item.href}>
                      {item.label}
                    </a>
                  ))}
                </div>
              </div>
            </nav>
          </div>

          <div className="site-header__right">
            <div className="search-box">
              <input type="text" placeholder="Поиск" className="search-input" />
            </div>

            {currentUser ? (
              <div className="user-actions">
                <span className="user-name">{currentUser.full_name}</span>
                <button
                  type="button"
                  className="logout-button"
                  onClick={handleLogout}
                  aria-label="Выйти из аккаунта"
                  title="Выйти"
                >
                  <svg
                    className="logout-button__icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M14 7L19 12L14 17"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M19 12H10"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M10 5H6C4.89543 5 4 5.89543 4 7V17C4 18.1046 4.89543 19 6 19H10"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="login-button"
                onClick={() => {
                  setPendingAuthorAfterRegister(false);
                  setAuthMode("login");
                  setIsAuthModalOpen(true);
                }}
              >
                Войти
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="page-content page-content--centered">
        <section className="hero hero--landing">
          <h1 className="hero__title hero__title--centered">Платформа для создания курсов</h1>

          <p className="hero__text hero__text--centered">
            Создавайте онлайн-курсы на нашей платформе без каких-либо знаний в программировании.
          </p>

          <div className="hero__actions hero__actions--centered">
            <button type="button" className="create-course-button">
              Создать курс
            </button>
          </div>
        </section>
      </main>

      <button
        type="button"
        className="become-author-fab"
        onClick={handleBecomeAuthorClick}
        aria-label="Стать автором"
      >
        <img
          className="become-author-fab__icon"
          src="/create_course_icon.svg"
          alt=""
          aria-hidden="true"
        />
      </button>

      {isAuthorOfferOpen ? (
        <div className="author-offer-overlay" onClick={() => setIsAuthorOfferOpen(false)}>
          <div
            className="author-offer-modal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="author-offer-modal__close"
              onClick={() => setIsAuthorOfferOpen(false)}
              aria-label="Закрыть"
            >
              x
            </button>

            <h2 className="author-offer-modal__title">Станьте автором StudyRoom</h2>

            <p className="author-offer-modal__text">
              Как автор вы сможете создавать курсы, добавлять уроки и управлять учебными материалами в личном кабинете.
            </p>
            {authorOfferError ? (
              <p className="author-offer-modal__error">{authorOfferError}</p>
            ) : null}

            <div className="author-offer-modal__actions">
              <button
                type="button"
                className="author-offer-modal__btn author-offer-modal__btn--primary"
                onClick={handleConfirmBecomeAuthorClick}
              >
                Да, хочу стать автором
              </button>

              <button
                type="button"
                className="author-offer-modal__btn author-offer-modal__btn--ghost"
                onClick={() => setIsAuthorOfferOpen(false)}
              >
                Пока нет
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <AuthModal
        isOpen={isAuthModalOpen}
        mode={authMode}
        onClose={handleAuthModalClose}
        onChangeMode={setAuthMode}
        onLogin={handleLoginSubmit}
        onRegister={handleRegisterSubmit}
        onGoogleAuth={handleGoogleAuth}
      />
    </div>
  );
}

export default App;
