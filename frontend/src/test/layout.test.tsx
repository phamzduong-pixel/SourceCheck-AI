/**
 * Test Suite for App Shell, Layout, Navigation, and System Status.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import {
  AIPreferencesProvider,
  UI_LANGUAGE_STORAGE_KEY,
  AI_LANGUAGE_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "../context/AIPreferencesContext";
import { AppLayout } from "../components/layout/AppLayout";
import { SystemStatusIndicator } from "../components/layout/SystemStatusIndicator";
import { UILanguageSelector } from "../components/layout/UILanguageSelector";
import { AILanguageSelector } from "../components/layout/AILanguageSelector";
import { ThemeToggle } from "../components/layout/ThemeToggle";
import { DashboardPage } from "../pages/DashboardPage";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";
import { TOKEN_STORAGE_KEY } from "../services/auth";
import { systemService } from "../services/system";
import conversationService from "../services/conversations";
import { FactCheckPage } from "@/pages";
import { DocumentsPage } from "@/pages/DocumentsPage";

describe("App Shell & Layout (FE-02, FE-04.2.1 & FE-04.2.2)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.spyOn(systemService, "getHealth").mockResolvedValue({
      status: "healthy",
      service: "SourceCheck AI",
      environment: "test",
    });
    vi.spyOn(systemService, "getReadiness").mockResolvedValue({
      status: "ready",
      database: "connected",
      redis: "connected",
      vector_db: "connected",
    });
  });

  describe("1. AppLayout & Navigation Structure", () => {
    it("renders sidebar, header, navigation links, and default outlet", async () => {
      // Mock authenticated user state
      localStorage.setItem(TOKEN_STORAGE_KEY, "mock-jwt-token");
      vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
        const url = String(input);
        if (url.includes("/auth/me")) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              success: true,
              data: {
                id: "u-123",
                email: "researcher@example.com",
                full_name: "Dr. Nguyen",
                role: "researcher",
                is_active: true,
                created_at: "2026-09-14T00:00:00Z",
              },
            }),
          } as Response;
        }
        if (url.includes("/health")) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              status: "healthy",
              service: "SourceCheck AI",
              environment: "dev",
            }),
          } as Response;
        }
        if (url.includes("/ready")) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              status: "ready",
              database: "connected",
              redis: "connected",
              vector_db: "connected",
            }),
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({ detail: "Not found" }),
        } as Response;
      });

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route
                  path="/qa"
                  element={<div data-testid="qa-outlet">QA Content</div>}
                />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>,
      );

      // Verify Brand in Sidebar
      expect(screen.getByTestId("app-sidebar")).toBeInTheDocument();
      expect(screen.getByText("SourceCheck")).toBeInTheDocument();

      // Verify Navigation items exist in sidebar
      const sidebarNav = screen.getByTestId("app-sidebar");
      expect(
        within(sidebarNav).getByTestId("sidebar-new-chat-btn"),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("button", {
          name: /tra cứu mới|new research/i,
        }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByTestId("sidebar-history-section"),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", {
          name: /kiểm chứng thông tin|fact-checking/i,
        }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", { name: /tài liệu|documents/i }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", {
          name: /tìm kiếm nguồn|search explorer/i,
        }),
      ).toBeInTheDocument();

      // Verify User Info in sidebar bottom
      await waitFor(() => {
        expect(screen.getByText("Dr. Nguyen")).toBeInTheDocument();
        expect(screen.getByText("researcher")).toBeInTheDocument();
        expect(
          within(screen.getByTestId("sidebar-user-section")).getByText(
            "Dr. Nguyen",
          ),
        ).toBeInTheDocument();
      });

      // Verify User Menu Trigger and open popup menu
      const userTrigger = screen.getByTestId("user-menu-trigger");
      expect(userTrigger).toBeInTheDocument();
      fireEvent.click(userTrigger);

      // Verify User Account popup menu opens and contains Sign out
      expect(screen.getByTestId("user-account-menu")).toBeInTheDocument();
      expect(screen.getByTestId("btn-signout")).toBeInTheDocument();

      // Verify Dashboard Page content rendered in outlet
      expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
    });

    it("toggles mobile menu when toggle button is clicked", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<div>Content</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>,
      );

      const sidebar = screen.getByTestId("app-sidebar");
      expect(sidebar).not.toHaveClass("open");

      const toggleBtn = screen.getByTestId("mobile-menu-toggle");
      fireEvent.click(toggleBtn);

      expect(sidebar).toHaveClass("open");

      // Click backdrop to close
      const backdrop = screen.getByTestId("sidebar-backdrop");
      fireEvent.click(backdrop);

      expect(sidebar).not.toHaveClass("open");

      await waitFor(() => {
        expect(screen.getByTestId("status-dot-ready")).toBeInTheDocument();
      });
    });
  });

  describe("2. Navigation Between Modules", () => {
    it("navigates to different feature routes when clicking sidebar links", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="/documents" element={<DocumentsPage />} />
                <Route path="/fact-check" element={<FactCheckPage />} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>,
      );

      // Initially on Dashboard
      expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();

      const sidebarNav = screen.getByTestId("app-sidebar");

      // Click Fact-Checking
      fireEvent.click(
        within(sidebarNav).getByRole("link", {
          name: /kiểm chứng thông tin|fact-checking/i,
        }),
      );
      await waitFor(() => {
        const placeholderFc = screen.getByTestId("placeholder-fact-check");
        expect(placeholderFc).toBeInTheDocument();
        expect(
          within(placeholderFc).getByText("Fact-Checking"),
        ).toBeInTheDocument();
      });

      // Click Documents
      fireEvent.click(
        within(sidebarNav).getByRole("link", { name: /tài liệu|documents/i }),
      );
      await waitFor(() => {
        const placeholderDoc = screen.getByTestId("placeholder-documents");
        expect(placeholderDoc).toBeInTheDocument();
        expect(
          within(placeholderDoc).getByText("Documents"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("3. SystemStatusIndicator Component", () => {
    it("shows Ready status when both health and readiness succeed", async () => {
      vi.spyOn(systemService, "getHealth").mockResolvedValueOnce({
        status: "healthy",
        service: "SourceCheck AI",
        environment: "dev",
      });
      vi.spyOn(systemService, "getReadiness").mockResolvedValueOnce({
        status: "ready",
        database: "connected",
        redis: "connected",
        vector_db: "connected",
      });

      render(<SystemStatusIndicator />);

      await waitFor(() => {
        expect(screen.getByText(/sẵn sàng|ready/i)).toBeInTheDocument();
        expect(screen.getByTestId("status-dot-ready")).toBeInTheDocument();
      });
    });

    it("shows Degraded status when only health succeeds", async () => {
      vi.spyOn(systemService, "getHealth").mockResolvedValueOnce({
        status: "healthy",
        service: "SourceCheck AI",
        environment: "dev",
      });
      vi.spyOn(systemService, "getReadiness").mockRejectedValueOnce(
        new Error("DB connection refused"),
      );

      render(<SystemStatusIndicator />);

      await waitFor(() => {
        expect(
          screen.getByText(/giảm hiệu năng|degraded/i),
        ).toBeInTheDocument();
        expect(screen.getByTestId("status-dot-degraded")).toBeInTheDocument();
      });
    });

    it("handles server offline gracefully without throwing or crashing", async () => {
      vi.spyOn(systemService, "getHealth").mockRejectedValueOnce(
        new Error("Network down"),
      );
      vi.spyOn(systemService, "getReadiness").mockRejectedValueOnce(
        new Error("Network down"),
      );

      render(<SystemStatusIndicator />);

      await waitFor(() => {
        expect(screen.getByText(/ngoại tuyến|offline/i)).toBeInTheDocument();
        expect(screen.getByTestId("status-dot-offline")).toBeInTheDocument();
      });
    });
  });

  describe("4. DashboardPage Feature Cards", () => {
    it("renders all 4 feature cards with actionable links", () => {
      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>,
      );

      expect(screen.getByTestId("card-qa")).toHaveAttribute("href", "/qa");
      expect(screen.getByTestId("card-fact-check")).toHaveAttribute(
        "href",
        "/fact-check",
      );
      expect(screen.getByTestId("card-documents")).toHaveAttribute(
        "href",
        "/documents",
      );
      expect(screen.getByTestId("card-search")).toHaveAttribute(
        "href",
        "/search",
      );

      expect(screen.getByText("SourceCheck AI Workspace")).toBeInTheDocument();
      expect(screen.getByText("Khám phá Q&A")).toBeInTheDocument();
      expect(screen.getByText("Bắt đầu kiểm chứng")).toBeInTheDocument();
      expect(screen.getByText("Nạp tài liệu")).toBeInTheDocument();
      expect(screen.getByText("Tra cứu bằng chứng")).toBeInTheDocument();
    });
  });

  describe("5. Protected Routing & Logout in App Shell", () => {
    it("redirects unauthenticated user trying to access AppLayout to /login", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
              </Route>
              <Route
                path="/login"
                element={<div data-testid="login-redirect">Login Page</div>}
              />
            </Routes>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("login-redirect")).toBeInTheDocument();
      });
    });

    it("logs user out and clears token when Sign out button is clicked in header", async () => {
      localStorage.setItem(TOKEN_STORAGE_KEY, "valid-token-777");

      vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
        const url = String(input);
        if (url.includes("/auth/me")) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              success: true,
              data: {
                id: "u-logout",
                email: "user@example.com",
                full_name: "Logged In User",
                role: "user",
                is_active: true,
                created_at: "2026-09-14T00:00:00Z",
              },
            }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({ status: "healthy", database: "connected" }),
        } as Response;
      });

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
              </Route>
              <Route
                path="/login"
                element={<div data-testid="login-redirect">Login Page</div>}
              />
            </Routes>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Logged In User")).toBeInTheDocument();
      });

      // Open user menu dropdown
      const userTrigger = screen.getByTestId("user-menu-trigger");
      fireEvent.click(userTrigger);

      const signOutBtn = screen.getByTestId("btn-signout");
      fireEvent.click(signOutBtn);

      await waitFor(() => {
        expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
        expect(screen.getByTestId("login-redirect")).toBeInTheDocument();
      });
    });
  });

  describe("6. Demo User Menu in Sidebar (FE-04.2.1)", () => {
    beforeEach(() => {
      localStorage.setItem(TOKEN_STORAGE_KEY, "mock-token");
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          success: true,
          data: {
            id: "u-demo",
            email: "demouser@sourcecheck.ai",
            full_name: "Minh Quan",
            role: "editor",
            is_active: true,
            created_at: "2026-09-14T00:00:00Z",
          },
        }),
      } as Response);
    });

    it("renders user details in sidebar bottom and toggles account menu on click", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route index element={<div>Dashboard</div>} />
                </Route>
              </Routes>
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      // Verify user info is visible in sidebar card
      await waitFor(() => {
        expect(screen.getByTestId("sidebar-user-name")).toHaveTextContent(
          "Minh Quan",
        );
        expect(screen.getByText("editor")).toBeInTheDocument();
      });

      // Menu should initially not be open
      expect(screen.queryByTestId("user-account-menu")).not.toBeInTheDocument();

      // Click trigger to open menu
      const trigger = screen.getByTestId("user-menu-trigger");
      fireEvent.click(trigger);

      // Account menu should now be visible with user info
      expect(screen.getByTestId("user-account-menu")).toBeInTheDocument();
      expect(screen.getByTestId("dropdown-user-name")).toHaveTextContent(
        "Minh Quan",
      );
      expect(screen.getByTestId("dropdown-user-email")).toHaveTextContent(
        "demouser@sourcecheck.ai",
      );
      expect(screen.getByTestId("dropdown-user-role")).toHaveTextContent(
        "editor",
      );
      expect(screen.getByTestId("btn-signout")).toBeInTheDocument();

      // Click trigger again to close menu
      fireEvent.click(trigger);
      expect(screen.queryByTestId("user-account-menu")).not.toBeInTheDocument();
    });

    it("closes account menu on Escape key press", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route index element={<div>Dashboard</div>} />
                </Route>
              </Routes>
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("sidebar-user-name")).toBeInTheDocument();
      });

      // Open menu
      fireEvent.click(screen.getByTestId("user-menu-trigger"));
      expect(screen.getByTestId("user-account-menu")).toBeInTheDocument();

      // Press Escape
      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
      expect(screen.queryByTestId("user-account-menu")).not.toBeInTheDocument();
    });

    it("closes account menu on click outside", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route
                    index
                    element={<div data-testid="outside-area">Dashboard</div>}
                  />
                </Route>
              </Routes>
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("sidebar-user-name")).toBeInTheDocument();
      });

      // Open menu
      fireEvent.click(screen.getByTestId("user-menu-trigger"));
      expect(screen.getByTestId("user-account-menu")).toBeInTheDocument();

      // Click outside
      fireEvent.mouseDown(screen.getByTestId("outside-area"));
      expect(screen.queryByTestId("user-account-menu")).not.toBeInTheDocument();
    });
  });

  describe("7. AI Response Language Selector (FE-04.2.1)", () => {
    it("defaults to Vietnamese (vi) and updates to English (en) with persistence", async () => {
      render(
        <AIPreferencesProvider>
          <AILanguageSelector />
        </AIPreferencesProvider>,
      );

      const btnVi = screen.getByTestId("ai-lang-btn-vi");
      const btnEn = screen.getByTestId("ai-lang-btn-en");

      // Default is 'vi'
      expect(btnVi).toHaveClass("active");
      expect(btnVi).toHaveAttribute("aria-pressed", "true");
      expect(btnEn).not.toHaveClass("active");

      // Click 'EN'
      fireEvent.click(btnEn);
      expect(btnEn).toHaveClass("active");
      expect(btnVi).not.toHaveClass("active");
      expect(localStorage.getItem(AI_LANGUAGE_STORAGE_KEY)).toBe("en");

      // Click 'VI'
      fireEvent.click(btnVi);
      expect(btnVi).toHaveClass("active");
      expect(btnEn).not.toHaveClass("active");
      expect(localStorage.getItem(AI_LANGUAGE_STORAGE_KEY)).toBe("vi");
    });

    it("restores stored language preference from localStorage on mount", () => {
      localStorage.setItem(AI_LANGUAGE_STORAGE_KEY, "en");

      render(
        <AIPreferencesProvider>
          <AILanguageSelector />
        </AIPreferencesProvider>,
      );

      const btnEn = screen.getByTestId("ai-lang-btn-en");
      expect(btnEn).toHaveClass("active");
    });
  });

  describe("8. Light / Dark Mode Theme Toggle (FE-04.2.1)", () => {
    it("toggles between light and dark themes, setting data-theme and persisting in localStorage", () => {
      render(
        <AIPreferencesProvider>
          <ThemeToggle />
        </AIPreferencesProvider>,
      );

      const toggleBtn = screen.getByTestId("theme-toggle");

      // Default should be light mode
      expect(document.documentElement.getAttribute("data-theme")).toBe("light");

      // Toggle to dark mode
      fireEvent.click(toggleBtn);
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");

      // Toggle back to light mode
      fireEvent.click(toggleBtn);
      expect(document.documentElement.getAttribute("data-theme")).toBe("light");
      expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    });

    it("restores saved theme preference from localStorage on mount", () => {
      localStorage.setItem(THEME_STORAGE_KEY, "dark");

      render(
        <AIPreferencesProvider>
          <ThemeToggle />
        </AIPreferencesProvider>,
      );

      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });
  });

  describe("9. UI Language & AI Response Language Separation (FE-04.2.2)", () => {
    it("defaults to Vietnamese (vi) for both UI and AI Response Language", () => {
      render(
        <AIPreferencesProvider>
          <div data-testid="selectors-wrap">
            <UILanguageSelector />
            <AILanguageSelector />
          </div>
        </AIPreferencesProvider>,
      );

      // UI Language is 'vi' by default
      expect(screen.getByTestId("ui-lang-btn-vi")).toHaveClass("active");
      expect(screen.getByTestId("ui-lang-btn-en")).not.toHaveClass("active");

      // AI Language is 'vi' by default
      expect(screen.getByTestId("ai-lang-btn-vi")).toHaveClass("active");
      expect(screen.getByTestId("ai-lang-btn-en")).not.toHaveClass("active");
    });

    it("switches UI Language independently without affecting AI Response Language and persists in localStorage", () => {
      render(
        <AIPreferencesProvider>
          <div data-testid="selectors-wrap">
            <UILanguageSelector />
            <AILanguageSelector />
          </div>
        </AIPreferencesProvider>,
      );

      const uiEnBtn = screen.getByTestId("ui-lang-btn-en");
      const aiViBtn = screen.getByTestId("ai-lang-btn-vi");
      const aiEnBtn = screen.getByTestId("ai-lang-btn-en");

      // Switch UI to EN
      fireEvent.click(uiEnBtn);
      expect(uiEnBtn).toHaveClass("active");
      expect(localStorage.getItem(UI_LANGUAGE_STORAGE_KEY)).toBe("en");

      // AI Language should remain unchanged ('vi')
      expect(aiViBtn).toHaveClass("active");
      expect(aiEnBtn).not.toHaveClass("active");

      // Now switch AI to EN
      fireEvent.click(aiEnBtn);
      expect(aiEnBtn).toHaveClass("active");
      expect(localStorage.getItem(AI_LANGUAGE_STORAGE_KEY)).toBe("en");

      // UI remains EN
      expect(uiEnBtn).toHaveClass("active");

      // Switch UI back to VI
      const uiViBtn = screen.getByTestId("ui-lang-btn-vi");
      fireEvent.click(uiViBtn);
      expect(uiViBtn).toHaveClass("active");
      expect(localStorage.getItem(UI_LANGUAGE_STORAGE_KEY)).toBe("vi");

      // AI remains EN
      expect(aiEnBtn).toHaveClass("active");
    });

    it("updates navigation and sidebar text when UI Language is toggled between vi and en", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route index element={<div>Dashboard Page</div>} />
                </Route>
              </Routes>
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      const sidebarNav = screen.getByTestId("app-sidebar");

      // Initially in Vietnamese
      expect(
        within(sidebarNav).getByRole("button", { name: /tra cứu mới/i }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", { name: /kiểm chứng thông tin/i }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", { name: /tài liệu/i }),
      ).toBeInTheDocument();
      expect(
        within(sidebarNav).getByRole("link", { name: /tìm kiếm nguồn/i }),
      ).toBeInTheDocument();

      // Open user menu and switch UI language to English
      const trigger = screen.getByTestId("user-menu-trigger");
      fireEvent.click(trigger);
      const userMenu = screen.getByTestId("user-account-menu");
      const uiEnBtn = within(userMenu).getByTestId("ui-lang-btn-en");
      fireEvent.click(uiEnBtn);

      // Now in English
      await waitFor(() => {
        expect(
          within(sidebarNav).getByRole("button", { name: /new research/i }),
        ).toBeInTheDocument();
        expect(
          within(sidebarNav).getByRole("link", { name: /fact-checking/i }),
        ).toBeInTheDocument();
        expect(
          within(sidebarNav).getByRole("link", { name: /documents/i }),
        ).toBeInTheDocument();
        expect(
          within(sidebarNav).getByRole("link", { name: /search explorer/i }),
        ).toBeInTheDocument();
      });

      // Switch back to Vietnamese
      const uiViBtn = within(userMenu).getByTestId("ui-lang-btn-vi");
      fireEvent.click(uiViBtn);

      await waitFor(() => {
        expect(
          within(sidebarNav).getByRole("button", { name: /tra cứu mới/i }),
        ).toBeInTheDocument();
      });
    });

    it("restores stored UI language preference from localStorage on mount", () => {
      localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, "en");

      render(
        <AIPreferencesProvider>
          <UILanguageSelector />
        </AIPreferencesProvider>,
      );

      expect(screen.getByTestId("ui-lang-btn-en")).toHaveClass("active");
    });
  });

  describe("7. Conversation Deletion & Management (CHAT-02.5)", () => {
    const mockConvs = [
      {
        id: "c-1",
        title: "Nghiên cứu WTO",
        is_pinned: true,
        created_at: "2026-09-14T00:00:00Z",
        updated_at: "2026-09-14T00:00:00Z",
      },
      {
        id: "c-2",
        title: "An ninh mạng 2026",
        is_pinned: false,
        created_at: "2026-09-14T00:00:00Z",
        updated_at: "2026-09-14T00:00:00Z",
      },
    ];

    it("renders conversation context menu with Rename, Pin, and Delete options", async () => {
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        mockConvs,
      );

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-1"),
        ).toBeInTheDocument();
      });

      // Open menu
      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-1"));

      expect(
        screen.getByTestId("conversation-action-menu-c-1"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("action-rename-c-1")).toBeInTheDocument();
      expect(screen.getByTestId("action-pin-c-1")).toBeInTheDocument();
      expect(screen.getByTestId("action-delete-c-1")).toBeInTheDocument();
    });

    it("opens confirmation modal on Delete click and cancels when Hủy is clicked", async () => {
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        mockConvs,
      );

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-2"),
        ).toBeInTheDocument();
      });

      // Open menu and click Delete
      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-2"));
      fireEvent.click(screen.getByTestId("action-delete-c-2"));

      // Modal appears
      expect(
        screen.getByTestId("delete-conversation-modal"),
      ).toBeInTheDocument();
      expect(screen.getByText(/Xóa cuộc trò chuyện\?/i)).toBeInTheDocument();
      expect(
        screen.getByText(
          /Cuộc trò chuyện và toàn bộ nội dung bên trong sẽ bị xóa/i,
        ),
      ).toBeInTheDocument();

      // Click Cancel button
      fireEvent.click(screen.getByTestId("btn-modal-cancel"));

      // Modal closes, item remains
      expect(
        screen.queryByTestId("delete-conversation-modal"),
      ).not.toBeInTheDocument();
      expect(screen.getByText("An ninh mạng 2026")).toBeInTheDocument();
    });

    it("deletes inactive conversation: removes item from sidebar without full reload", async () => {
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        mockConvs,
      );
      const deleteSpy = vi
        .spyOn(conversationService, "deleteConversation")
        .mockResolvedValue();

      render(
        <MemoryRouter initialEntries={["/chat/c-1"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-2"),
        ).toBeInTheDocument();
      });

      // Delete inactive conv c-2
      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-2"));
      fireEvent.click(screen.getByTestId("action-delete-c-2"));
      fireEvent.click(screen.getByTestId("btn-modal-confirm"));

      await waitFor(() => {
        expect(deleteSpy).toHaveBeenCalledWith("c-2");
        expect(screen.queryByText("An ninh mạng 2026")).not.toBeInTheDocument();
        // Conv c-1 remains in sidebar
        expect(screen.getByText("Nghiên cứu WTO")).toBeInTheDocument();
      });
    });

    it("handles DELETE API error: keeps conversation item and displays error alert", async () => {
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        mockConvs,
      );
      vi.spyOn(conversationService, "deleteConversation").mockRejectedValue(
        new Error("Backend error"),
      );

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-1"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-1"));
      fireEvent.click(screen.getByTestId("action-delete-c-1"));
      fireEvent.click(screen.getByTestId("btn-modal-confirm"));

      await waitFor(() => {
        expect(screen.getByTestId("delete-error-alert")).toBeInTheDocument();
        expect(screen.getByText("Nghiên cứu WTO")).toBeInTheDocument();
      });
    });

    it("displays empty history state when all conversations are deleted", async () => {
      const singleConv = [
        {
          id: "c-last",
          title: "Cuộc trò chuyện duy nhất",
          is_pinned: false,
          created_at: "",
          updated_at: "",
        },
      ];
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        singleConv,
      );
      vi.spyOn(conversationService, "deleteConversation").mockResolvedValue();

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-last"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-last"));
      fireEvent.click(screen.getByTestId("action-delete-c-last"));
      fireEvent.click(screen.getByTestId("btn-modal-confirm"));

      await waitFor(() => {
        expect(screen.getByTestId("sidebar-history-empty")).toBeInTheDocument();
      });
    });

    it("supports English UI language for delete confirmation modal", async () => {
      localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, "en");
      vi.spyOn(conversationService, "listConversations").mockResolvedValue(
        mockConvs,
      );

      render(
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <AIPreferencesProvider>
              <AppLayout />
            </AIPreferencesProvider>
          </AuthProvider>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("conversation-menu-trigger-c-1"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("conversation-menu-trigger-c-1"));
      fireEvent.click(screen.getByTestId("action-delete-c-1"));

      expect(screen.getByText("Delete conversation?")).toBeInTheDocument();
      expect(
        screen.getByText(
          "This conversation and all its contents will be deleted. This action cannot be undone.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByTestId("btn-modal-cancel")).toHaveTextContent(
        "Cancel",
      );
      expect(screen.getByTestId("btn-modal-confirm")).toHaveTextContent(
        "Delete",
      );
    });
  });
});
