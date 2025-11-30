import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);
// this is the entry point of the application,
//  ! is used to tell typescript that the element is not null
