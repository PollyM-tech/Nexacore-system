import logo from "@/app/assets/logo.png";

type Props = {
  compact?: boolean;
  size?: "navigation" | "sidebar" | "footer" | "login";
};

export function Brand({ compact, size = "navigation" }: Props) {
  const sizing = size === "login"
    ? "w-56 sm:w-64 xl:w-80"
    : size === "sidebar"
      ? "w-6 sm:w-7"
    : size === "footer"
      ? "w-24 sm:w-28"
      : compact ? "w-12" : "w-14";

  // Preserve the official asset's full square canvas and opaque background.
  return <img src={logo} alt="Lintech" width={1024} height={1024}
    className={`block h-auto max-w-full shrink-0 object-contain ${sizing}`} />;
}
