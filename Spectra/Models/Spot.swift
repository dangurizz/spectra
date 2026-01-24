import Foundation

struct Spot: Identifiable, Codable {
    let id: UUID
    let name: String
    let latitude: Double
    let longitude: Double
    let region: String
    let nearestBuoyId: String?
    let nearestWindStation: String?
    let nearestTideStation: String?
}
