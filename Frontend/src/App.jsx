import { useState } from "react";
import "./App.css";
import AuthModal from "./components/AuthModal";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1/auth";


function App() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
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
            Создавайте онлайн-курсы на нашей платформе без каких либо знаний в программировании.
          </p>

          <div className="hero__actions hero__actions--centered">
            <button type="button" className="create-course-button">
              Создать курс
            </button>
          </div>
        </section>
      </main>

      <AuthModal
        isOpen={isAuthModalOpen}
        mode={authMode}
        onClose={() => setIsAuthModalOpen(false)}
        onChangeMode={setAuthMode}
        onLogin={handleLoginSubmit}
        onRegister={handleRegisterSubmit}
        onGoogleAuth={handleGoogleAuth}
      />
    </div>
  );
}

export default App;

