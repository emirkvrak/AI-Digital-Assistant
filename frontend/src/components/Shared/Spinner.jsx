import { useTranslation } from "react-i18next";
import "./Spinner.module.css";

const Spinner = () => {
  const { t } = useTranslation();

  return (
    <div className="spinner-container">
      <div className="loading-spinner" />
      <p style={{ marginTop: "12px", fontSize: "1rem", color: "#555" }}>
        {t("loading")}
      </p>
    </div>
  );
};

export default Spinner;
