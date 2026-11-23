import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Spinner } from "@/components/ui/Feedback";
import { AdminLayout } from "@/layouts/AdminLayout";
import { AppLayout } from "@/layouts/AppLayout";
import { GuestOnly, RequireAdmin, RequireAuth } from "@/layouts/guards";
import { PublicLayout } from "@/layouts/PublicLayout";
import { ShellByAuth } from "@/layouts/ShellByAuth";

const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));
const ForgotPassword = lazy(() => import("@/pages/ForgotPassword"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const TextAnalysis = lazy(() => import("@/pages/TextAnalysis"));
const ImageAnalysis = lazy(() => import("@/pages/ImageAnalysis"));
const VideoAnalysis = lazy(() => import("@/pages/VideoAnalysis"));
const MultimodalAnalysis = lazy(() => import("@/pages/MultimodalAnalysis"));
const UrlAnalysis = lazy(() => import("@/pages/UrlAnalysis"));
const EvidenceVerification = lazy(() => import("@/pages/EvidenceVerification"));
const AnalysisResult = lazy(() => import("@/pages/AnalysisResult"));
const AnalysisReport = lazy(() => import("@/pages/AnalysisReport"));
const History = lazy(() => import("@/pages/History"));
const Profile = lazy(() => import("@/pages/Profile"));
const Settings = lazy(() => import("@/pages/Settings"));
const Contact = lazy(() => import("@/pages/Contact"));
const Admin = lazy(() => import("@/pages/Admin"));
const AdminUsers = lazy(() => import("@/pages/AdminUsers"));
const ModelInfo = lazy(() => import("@/pages/ModelInfo"));
const About = lazy(() => import("@/pages/About"));
const Methodology = lazy(() => import("@/pages/Methodology"));
const NotFound = lazy(() => import("@/pages/NotFound"));

export default function App() {
  return (
    <Suspense fallback={<div className="grid min-h-screen place-items-center"><Spinner label="Loading page" /></div>}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<Landing />} />
        </Route>

        <Route element={<GuestOnly />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ForgotPassword />} />
        </Route>

        <Route element={<ShellByAuth />}>
          <Route path="/about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analyze/text" element={<TextAnalysis />} />
            <Route path="/analyze/image" element={<ImageAnalysis />} />
            <Route path="/analyze/video" element={<VideoAnalysis />} />
            <Route path="/analyze/multimodal" element={<MultimodalAnalysis />} />
            <Route path="/analyze/url" element={<UrlAnalysis />} />
            <Route path="/analyze/evidence" element={<EvidenceVerification />} />
            <Route path="/analysis/:id" element={<AnalysisResult />} />
            <Route path="/analysis/:id/report" element={<AnalysisReport />} />
            <Route path="/history" element={<History />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/contact" element={<Contact />} />
          </Route>

          {/* The administrator console. The server refuses these calls to anyone else too; this keeps the pages out of sight. */}
          <Route element={<RequireAdmin />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<Admin />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/models" element={<ModelInfo />} />
              <Route path="/admin/methodology" element={<Methodology />} />
            </Route>
          </Route>
          {/* The old public addresses of the technical pages now lead to the console, which sends everyone else home. */}
          <Route path="/models" element={<Navigate to="/admin/models" replace />} />
          <Route path="/methodology" element={<Navigate to="/admin/methodology" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
