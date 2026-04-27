import { useState } from "react";
import "./App.css";

function App() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");


  const platformMenuItems = [
    { label: "О платформе", href: "#" },
  ];

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
              <input
                type="text"
                placeholder="Поиск"
                className="search-input"
              />
            </div>

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
          </div>
        </div>
      </header>

      <main className="page-content page-content--centered">
  <section className="hero hero--landing">
    <h1 className="hero__title hero__title--centered">
      Платформа для создания курсов
    </h1>

    <p className="hero__text hero__text--centered">
      Создавайте онлайн-курсы на нашей платформе без каких либо знаний в
      программировании.
    </p>

    <div className="hero__actions hero__actions--centered">
      <button type="button" className="create-course-button">
        Создать курс
      </button>
    </div>
  </section>
</main>

{isAuthModalOpen && (
  <div className="modal-overlay" onClick={() => setIsAuthModalOpen(false)}>
    <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        className="modal-close"
        onClick={() => setIsAuthModalOpen(false)}
      >
        ×
      </button>

      <div className="auth-tabs">
        <button
          type="button"
          className={`auth-tab ${authMode === "login" ? "auth-tab--active" : ""}`}
          onClick={() => setAuthMode("login")}
        >
          Войти
        </button>

        <button
          type="button"
          className={`auth-tab ${authMode === "register" ? "auth-tab--active" : ""}`}
          onClick={() => setAuthMode("register")}
        >
          Регистрация
        </button>
      </div>

      <h2 className="auth-modal__title">
        {authMode === "login" ? "Вход в аккаунт" : "Создание аккаунта"}
      </h2>

      <p className="auth-modal__text">
        {authMode === "login"
          ? "Войди через email и пароль или используй Google."
          : "Зарегистрируй аккаунт через email и пароль или через Google."}
      </p>

      <form className="auth-form">
        {authMode === "register" && (
          <label className="auth-form__field">
            <span>Имя</span>
            <input type="text" placeholder="Введите имя" />
          </label>
        )}

        <label className="auth-form__field">
          <span>Email</span>
          <input type="email" placeholder="Введите email" />
        </label>

        <label className="auth-form__field">
          <span>Пароль</span>
          <input type="password" placeholder="Введите пароль" />
        </label>

        <button type="button" className="auth-submit-button">
          {authMode === "login" ? "Войти" : "Зарегистрироваться"}
        </button>
      </form>

      <div className="auth-divider">
        <span>или</span>
      </div>

      <button type="button" className="google-auth-button">
        Продолжить через Google
      </button>
    </div>
  </div>
)}

    </div>
  );
}

export default App;
