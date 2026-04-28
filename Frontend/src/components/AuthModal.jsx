import { useEffect, useState } from "react";
import "./AuthModal.css";

const initialLoginForm = {
  email: "",
  password: "",
};

const initialRegisterForm = {
  name: "",
  email: "",
  password: "",
  confirmPassword: "",
};

function AuthModal({
  isOpen,
  mode,
  onClose,
  onChangeMode,
  onLogin,
  onRegister,
  onGoogleAuth,
}) {
  const [loginForm, setLoginForm] = useState(initialLoginForm);
  const [registerForm, setRegisterForm] = useState(initialRegisterForm);
  const [loadingAction, setLoadingAction] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setError("");
        setSuccess("");
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const isLoading = loadingAction !== null;

  const handleLoginFieldChange = (event) => {
    const { name, value } = event.target;

    setLoginForm((currentState) => ({
      ...currentState,
      [name]: value,
    }));
  };

  const handleRegisterFieldChange = (event) => {
    const { name, value } = event.target;

    setRegisterForm((currentState) => ({
      ...currentState,
      [name]: value,
    }));
  };

  const handleLoginSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!loginForm.email.trim() || !loginForm.password.trim()) {
      setError("Заполните email и пароль.");
      return;
    }

    setLoadingAction("login");

    try {
      const response = await onLogin?.({
        email: loginForm.email.trim(),
        password: loginForm.password,
      });

      setSuccess(response?.message ?? "Вход выполнен.");
    } catch (submitError) {
      setError(submitError?.message ?? "Не удалось выполнить вход.");
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRegisterSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!registerForm.name.trim()) {
      setError("Введите имя.");
      return;
    }

    if (!registerForm.email.trim() || !registerForm.password.trim()) {
      setError("Заполните email и пароль.");
      return;
    }

    if (registerForm.password.length < 8) {
      setError("Пароль должен содержать минимум 8 символов.");
      return;
    }

    if (registerForm.password !== registerForm.confirmPassword) {
      setError("Пароли не совпадают.");
      return;
    }

    setLoadingAction("register");

    try {
      const response = await onRegister?.({
        name: registerForm.name.trim(),
        email: registerForm.email.trim(),
        password: registerForm.password,
        confirmPassword: registerForm.confirmPassword,
      });

      setSuccess(response?.message ?? "Аккаунт создан.");
    } catch (submitError) {
      setError(submitError?.message ?? "Не удалось создать аккаунт.");
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGoogleButtonClick = async () => {
    setError("");
    setSuccess("");
    setLoadingAction("google");

    try {
      const response = await onGoogleAuth?.();
      setSuccess(response?.message ?? "Переходим к Google.");
    } catch (submitError) {
      setError(submitError?.message ?? "Не удалось запустить вход через Google.");
    } finally {
      setLoadingAction(null);
    }
  };

  const handleClose = () => {
    setError("");
    setSuccess("");
    onClose();
  };

  const handleLoginTabClick = () => {
    setError("");
    setSuccess("");
    onChangeMode("login");
  };

  const handleRegisterTabClick = () => {
    setError("");
    setSuccess("");
    onChangeMode("register");
  };

  const formTitle = mode === "login" ? "Вход в аккаунт" : "Создание аккаунта";
  const formDescription =
    mode === "login"
      ? "Войдите через email и пароль или используйте Google."
      : "Зарегистрируйте аккаунт через email и пароль или через Google.";

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="auth-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <button
          type="button"
          className="modal-close"
          onClick={handleClose}
          aria-label="Закрыть окно"
        >
          x
        </button>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === "login" ? "auth-tab--active" : ""}`}
            onClick={handleLoginTabClick}
            disabled={isLoading}
          >
            Войти
          </button>

          <button
            type="button"
            className={`auth-tab ${mode === "register" ? "auth-tab--active" : ""}`}
            onClick={handleRegisterTabClick}
            disabled={isLoading}
          >
            Регистрация
          </button>
        </div>

        <h2 className="auth-modal__title" id="auth-modal-title">
          {formTitle}
        </h2>

        <p className="auth-modal__text">{formDescription}</p>

        {error ? <p className="auth-message auth-message--error">{error}</p> : null}
        {success ? <p className="auth-message auth-message--success">{success}</p> : null}

        <form
          className="auth-form"
          onSubmit={mode === "login" ? handleLoginSubmit : handleRegisterSubmit}
        >
          {mode === "register" ? (
            <label className="auth-form__field">
              <span>Имя</span>
              <input
                type="text"
                name="name"
                placeholder="Введите полное имя"
                value={registerForm.name}
                onChange={handleRegisterFieldChange}
                disabled={isLoading}
              />
            </label>
          ) : null}

          <label className="auth-form__field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              placeholder="Введите email"
              value={mode === "login" ? loginForm.email : registerForm.email}
              onChange={mode === "login" ? handleLoginFieldChange : handleRegisterFieldChange}
              disabled={isLoading}
            />
          </label>

          <label className="auth-form__field">
            <span>Пароль</span>
            <input
              type="password"
              name="password"
              placeholder="Введите пароль"
              value={mode === "login" ? loginForm.password : registerForm.password}
              onChange={mode === "login" ? handleLoginFieldChange : handleRegisterFieldChange}
              disabled={isLoading}
            />
          </label>

          {mode === "register" ? (
            <label className="auth-form__field">
              <span>Повторите пароль</span>
              <input
                type="password"
                name="confirmPassword"
                placeholder="Повторите пароль"
                value={registerForm.confirmPassword}
                onChange={handleRegisterFieldChange}
                disabled={isLoading}
              />
            </label>
          ) : null}

          <button type="submit" className="auth-submit-button" disabled={isLoading}>
            {loadingAction === "login" && mode === "login"
              ? "Входим..."
              : loadingAction === "register" && mode === "register"
                ? "Создаем аккаунт..."
                : mode === "login"
                  ? "Войти"
                  : "Зарегистрироваться"}
          </button>
        </form>

        <div className="auth-divider">
          <span>или</span>
        </div>

        <button
          type="button"
          className="google-auth-button"
          onClick={handleGoogleButtonClick}
          disabled={isLoading}
        >
          {loadingAction === "google" ? "Подключаем Google..." : "Продолжить через Google"}
        </button>
      </div>
    </div>
  );
}

export default AuthModal;
