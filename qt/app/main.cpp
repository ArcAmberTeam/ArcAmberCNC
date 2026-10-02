#include <QFontDatabase>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickStyle>

int main(int argc, char *argv[])
{
    QCoreApplication::setAttribute(Qt::AA_DontUseNativeMenuBar);
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("BetterLinuxCNC"));
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.0"));
    QCoreApplication::setOrganizationName(QStringLiteral("BetterLinuxCNC"));
    QQuickStyle::setStyle(QStringLiteral("Basic"));

    const auto families = QFontDatabase::families();
    for (const auto &family : {QStringLiteral("Inter"), QStringLiteral("Noto Sans CJK SC"),
                              QStringLiteral("PingFang SC"), QStringLiteral("Microsoft YaHei")}) {
        if (families.contains(family)) {
            QFont font(family);
            font.setPixelSize(13);
            app.setFont(font);
            break;
        }
    }

    QQmlApplicationEngine engine;
    engine.addImportPath(QStringLiteral("qrc:/qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, [] { QCoreApplication::exit(1); }, Qt::QueuedConnection);
    engine.load(QUrl(QStringLiteral("qrc:/qml/Main.qml")));
    return app.exec();
}
