import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Zap, FileText, Search, BarChart3 } from "lucide-react";
import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function Landing() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      alert(error.message);
    } else {
      window.location.href = "/";
    }
    setLoading(false);
  };

  const handleSignUp = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      alert(error.message);
    } else {
      alert("Check your email to confirm your account.");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50">
      {/* Hero Section */}
      <div className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Intelligent Construction Drawing Comparison
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Upload your construction drawings and let AI detect changes between versions automatically. 
            Save time, reduce errors, and maintain project accuracy with BuildTrace AI.
          </p>
          <div className="max-w-md mx-auto bg-white rounded-xl shadow p-6 text-left">
            <div className="space-y-3">
              <input
                type="email"
                placeholder="Email"
                className="w-full border rounded px-3 py-2"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                type="password"
                placeholder="Password"
                className="w-full border rounded px-3 py-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <div className="flex gap-3">
                <Button size="lg" className="flex-1" onClick={handleSignIn} disabled={loading}>
                  Sign In
                </Button>
                <Button size="lg" variant="secondary" className="flex-1" onClick={handleSignUp} disabled={loading}>
                  Sign Up
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Why Choose BuildTrace AI?
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <Card className="text-center">
              <CardHeader>
                <Zap className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                <CardTitle>Fast Processing</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  AI-powered analysis detects changes in minutes, not hours
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <FileText className="w-12 h-12 text-green-600 mx-auto mb-4" />
                <CardTitle>Multiple Formats</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Support for PDF, DWG, DXF, PNG, and JPG files up to 50MB
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <Search className="w-12 h-12 text-purple-600 mx-auto mb-4" />
                <CardTitle>Smart Detection</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Automatically categorizes changes by discipline and importance
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="text-center">
              <CardHeader>
                <BarChart3 className="w-12 h-12 text-orange-600 mx-auto mb-4" />
                <CardTitle>Detailed Reports</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Export comprehensive PDF reports with visual comparisons
                </CardDescription>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            How It Works
          </h2>
          <div className="space-y-8">
            <div className="flex items-center gap-6">
              <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                1
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload Your Drawings</h3>
                <p className="text-gray-600">
                  Upload your baseline and revised construction drawings in any supported format
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="w-12 h-12 bg-green-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                2
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Analysis</h3>
                <p className="text-gray-600">
                  Our advanced AI compares the drawings and identifies all changes automatically
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                3
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Review Results</h3>
                <p className="text-gray-600">
                  View detailed comparisons with side-by-side views and categorized change summaries
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="w-12 h-12 bg-orange-600 text-white rounded-full flex items-center justify-center text-xl font-bold flex-shrink-0">
                4
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Export & Share</h3>
                <p className="text-gray-600">
                  Generate comprehensive PDF reports to share with your team and stakeholders
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8 bg-blue-600">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to Transform Your Drawing Review Process?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join construction professionals who trust BuildTrace AI for accurate, fast drawing comparisons.
          </p>
          <Button 
            size="lg" 
            variant="secondary"
            className="text-lg px-8 py-6 h-auto"
            onClick={handleSignIn}
            data-testid="button-cta-login"
          >
            Start Free Comparison
          </Button>
        </div>
      </div>
    </div>
  );
}